import unittest

from home import MainQuestStep, Quest, own_home
from progress import (CLAIM_QUESTS, GO_TO_PORTAL, INTRO_3, INTRO_3_KILLS, INTRO_3_RESCUES,
                      PORTAL_TUTORIAL, TUTORIAL_NAME_10, complete_intro_quest, intro_main_steps,
                      intro_progress, record_main_quest)
from stream import Reader


def profile(step, kills=0, rescues=0):
    return {'tutorials': {'15600000': 0, str(PORTAL_TUTORIAL): step},
            'battle_progress': {'kills': kills, 'rescues': rescues, 'xp': 2 * kills}}


class IntroQuestTests(unittest.TestCase):
    def test_progress_is_capped_at_quest_targets(self):
        self.assertEqual(intro_progress(profile(GO_TO_PORTAL, 12, 1)), (12, 1))
        self.assertEqual(intro_progress(profile(GO_TO_PORTAL, 900, 40)), (50, 3))

    def test_go_to_portal_sends_live_intro_3_quests(self):
        (step,) = intro_main_steps(profile(GO_TO_PORTAL, 7, 2))
        self.assertEqual(step.reference, INTRO_3)
        self.assertFalse(step.claimed)
        self.assertEqual(step.quests, (Quest(INTRO_3_KILLS, 7, 50),
                                       Quest(INTRO_3_RESCUES, 2, 3, 'Civilian')))

    def test_no_main_quests_before_go_to_portal(self):
        self.assertEqual(intro_main_steps({'tutorials': {}}), ())
        self.assertEqual(intro_main_steps(profile(14200005)), ())

    def test_completion_requires_both_objectives(self):
        for kills, rescues in ((49, 3), (50, 2)):
            saved = profile(GO_TO_PORTAL, kills, rescues)
            self.assertFalse(complete_intro_quest(saved))
            self.assertEqual(saved['tutorials'][str(PORTAL_TUTORIAL)], GO_TO_PORTAL)
        saved = profile(GO_TO_PORTAL, 50, 3)
        self.assertTrue(complete_intro_quest(saved))
        self.assertEqual(saved['tutorials'][str(PORTAL_TUTORIAL)], CLAIM_QUESTS)
        self.assertFalse(complete_intro_quest(saved))  # Only once.

    def test_claimed_intro_unlocks_next_step_and_keeps_reported_steps(self):
        saved = profile(CLAIM_QUESTS, 50, 3)
        self.assertEqual(intro_main_steps(saved), (MainQuestStep(INTRO_3, claimed=True),
                                                   MainQuestStep(TUTORIAL_NAME_10, claimed=True)))
        saved['tutorials'][str(PORTAL_TUTORIAL)] = 0
        for command, step in ((575, 15400000), (575, 15400004), (576, 15400004), (575, 15400004)):
            record_main_quest(saved, command, step)
        self.assertEqual(saved['main_quests'], {'seen': [15400000, 15400004], 'done': [15400004]})
        refs = [step.reference for step in intro_main_steps(saved)]
        self.assertEqual(refs, [INTRO_3, TUTORIAL_NAME_10, 15400004])
        with self.assertRaises(ValueError):
            record_main_quest(saved, 575, 14200006)


class QuestEncodingTests(unittest.TestCase):
    def test_quests_get_unique_native_ids_and_next_id_header(self):
        steps = intro_main_steps(profile(GO_TO_PORTAL, 7, 2))
        body = own_home(1, main_steps=steps)
        empty = own_home(1)
        self.assertGreater(len(body), len(empty))
        # Locate the +a0 header: it follows the battle kit and the +90/+98 fields.
        kit = body.index((6700000).to_bytes(8, 'big')) + 8
        reader = Reader(body[kit:])
        self.assertEqual([reader.compact() for _ in range(3)], [0, 0, 0])
        reader.bit_boolean()
        self.assertEqual([reader.compact() for _ in range(2)], [0, 0])
        header = [reader.compact() for _ in range(4)]
        self.assertEqual(header, [2, 0, 0, 0])  # Next quest ID after IDs 0 and 1.
        self.assertEqual(reader.compact(), 2)
        self.assertEqual([reader.compact() for _ in range(4)], [0, 1, 7, 50])

    def test_saved_xp_is_the_avatar_xp_point_resource(self):
        body = own_home(1, xp=1551)
        self.assertEqual(len(body), len(own_home(1)) + 16)
        self.assertIn((300020).to_bytes(8, 'big') + (1551).to_bytes(4, 'big') + bytes(4), body)
        with self.assertRaises(ValueError):
            own_home(1, xp=-1)


if __name__ == '__main__':
    unittest.main()
