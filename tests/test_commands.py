import unittest
from commands import decode_client_turn, UnsupportedCommand


class ClientTurnTests(unittest.TestCase):
    def test_observed_tutorial_turn(self):
        # Native client: frame 0, time 8247, one Portal tutorial step 4.
        payload = bytes.fromhex('000000000000002037010000023e03b780017f81a6f00e84b3c50d')
        turn = decode_client_turn(payload)
        self.assertEqual((turn.frame, turn.client_time), (0, 8247))
        command, = turn.commands
        self.assertEqual((command.command_type, command.tick, command.game_id, command.account_id),
                         (574, 8247, -1, 0))
        self.assertEqual(command.fields, {'tutorial': 15600001, 'step': 14200004})
        for length in range(len(payload)):
            with self.assertRaises(ValueError):
                decode_client_turn(payload[:length])

    def test_presence_bits_span_multiple_commands_and_scalar_fields(self):
        payload = bytes.fromhex('0000000000000000030400000230db037f0000023c037f0000024f037f060000023e037f80a6f00e80b3c50d')
        turn = decode_client_turn(payload)
        self.assertEqual([c.command_type for c in turn.commands], [560, 572, 591, 574])
        self.assertTrue(all((c.tick, c.game_id, c.account_id) == (3, -1, 0) for c in turn.commands))
        self.assertEqual(turn.commands[-1].fields, {'tutorial': 15600000, 'step': 14200000})

    def test_tutorial_completion_and_next_tutorial_in_same_turn(self):
        payload = bytes.fromhex('0000000000000020360300000240dbb680017f82f1d70e0000023eb680017f80a6f00e000000023eb680017f0081a6f00e84b3c50d')
        commands = decode_client_turn(payload).commands
        self.assertEqual(commands[0].fields, {'step': 15400002})
        self.assertEqual(commands[1].fields, {'tutorial': 15600000, 'step': 0})
        self.assertEqual(commands[2].fields, {'tutorial': 15600001, 'step': 14200004})

    def test_observed_character_editor_equip_turns(self):
        # Native client: tapping a face, then a hairstyle, in the editor.
        for payload, cosmetic in (('000000000000000266010000021f03a6097f9787e202', 2900439),
                                  ('000000000000000544010000021f0384157f9b87e202', 2900443)):
            command, = decode_client_turn(bytes.fromhex(payload)).commands
            self.assertEqual((command.command_type, command.game_id, command.account_id), (543, -1, 0))
            self.assertEqual(command.fields, {'cosmetic': cosmetic, 'slot': 0})

    def test_observed_main_quest_claim_turn(self):
        # Native client: claim_quest (569, quest index 0), then PortalSet3 Set3.
        payload = bytes.fromhex('00000000000000062502000002391ba5187f01000000023ea5187f88a6f00e9cb3c50d')
        claim, tutorial = decode_client_turn(payload).commands
        self.assertEqual((claim.command_type, claim.tick, claim.game_id), (569, 1573, -1))
        self.assertEqual(claim.fields, {'quests': (0,)})
        self.assertEqual(tutorial.fields, {'tutorial': 15600008, 'step': 14200028})

    def test_observed_cool_zone_turns(self):
        # Native client in the COOL zone: 593 names SocialHub; 583 reports the
        # MERCH SHOP feature-unlock screen (feature_unlock_screens instance 9).
        payload = bytes.fromhex('000000000000000008030000023cdb087f00000251087fa5c8b20a0000024f087f00')
        self.assertEqual([c.command_type for c in decode_client_turn(payload).commands], [572, 593, 591])
        self.assertEqual(decode_client_turn(payload).commands[1].fields, {'reference': 10900005})
        unlock, = decode_client_turn(bytes.fromhex('00000000000000061b0100000247039b187fa9858106')).commands
        self.assertEqual((unlock.command_type, unlock.fields), (583, {'feature': 6300009}))

    def test_quiet_turn_and_invalid_count_or_suffix(self):
        self.assertEqual(decode_client_turn(bytes(10)).commands, ())
        for payload in (bytes(9) + b'\x7f', bytes(11)):
            with self.assertRaises(ValueError):
                decode_client_turn(payload)

    def test_unknown_command_has_no_guessed_length(self):
        with self.assertRaises(UnsupportedCommand) as error:
            decode_client_turn(bytes(9) + b'\x01' + (2).to_bytes(4, 'big'))
        self.assertEqual((error.exception.command_type, error.exception.offset), (2, 10))


if __name__ == '__main__':
    unittest.main()
