// Research probe (never published): applies a marker look to the local player of each
// decoded scene-start (23491) and saves the client's own re-encode of the message.
const root='/data/user/0/com.supercell.moco.localtest/files/diagnostics/';
function save(name, data) { const file=new File(root+name,'wb');file.write(data);file.close(); }
const B=owner.base;
const fn=(a,r,p)=>new NativeFunction(B.add(a),r,p);
const vector=fn(0x725fac,'pointer',['pointer','int']);
const lookup=fn(0x82ab0c,'pointer',['pointer','uint64']);
const metaSkin=fn(0x73862c,'void',['pointer','pointer','int']);
const metaDye=fn(0x738ad0,'void',['pointer','pointer','int']);
const charSkin=fn(0x6f2624,'void',['pointer','pointer']);
const charDye=fn(0x6f2890,'void',['pointer','pointer']);
const dyeCtor=fn(0x86cc94,'void',['pointer','pointer']);
const alloc=fn(0xe771c0,'pointer',['uint64']);
const reset=fn(0x8d7b2c,'void',['pointer','pointer','int']);
const SKINS=[2900792,2900869];
const DYES=['4b9f0096-3fe2-6c29-ff90-f33fc826c375','4b9f0096-40de-a598-e05e-75c897fece02','4b9f0096-931a-bd76-f31a-74b6756bcfc9'];
let n=0;
function encode(msg){
 const out=alloc(262144);reset(msg.add(8),out,262144);
 new NativeFunction(msg.readPointer().add(0x10).readPointer(),'void',['pointer'])(msg);
 return msg.add(0x40).readPointer().readByteArray(msg.add(0x1c).readS32());
}
function dyeEntry(uuid){
 const raw=Memory.alloc(16);raw.writeByteArray(uuid.replace(/-/g,'').match(/../g).map(h=>parseInt(h,16)));
 const e=Memory.alloc(0x28);dyeCtor(e,raw);return e;
}
const keep=[];
Interceptor.attach(B.add(0x5bf784),{onEnter(args){
 const msg=args[1];const k=n++;
 try{
  const stream=msg.add(8),len=stream.add(0x18).readS32(),data=stream.add(0x38).readPointer();
  if(!data.isNull()&&len>0)save('look-'+k+'-wire.bin',data.readByteArray(len));
  const frame=msg.add(0xa0).readPointer().add(0x28).readPointer();
  const players=vector(frame,2009);
  log('Look probe scene '+k+' players='+players.add(12).readS32());
  if(players.add(12).readS32()<1)return;
  save('look-'+k+'-plain.bin',encode(msg));
  const player=players.readPointer().readPointer();
  let character=player.add(0xa8).readPointer();
  log('Look probe character '+character+' chars2001='+vector(frame,2001).add(12).readS32());
  const registry=B.add(0xfb8598).readPointer();
  const meta=player.add(0x1e8).readPointer();
  log('Look probe meta skins='+meta.add(0xec).readS32()+' dyes='+meta.add(0x114).readS32()+' orig='+meta.add(0x124).readS32());
  for(const id of SKINS){const d=lookup(registry,id);if(d.isNull())throw new Error('no data '+id);metaSkin(player,d.sub(0x18),1);if(!character.isNull())charSkin(character,d.sub(0x18));}
  for(const u of DYES){const e=dyeEntry(u);keep.push(e);metaDye(player,e,1);if(!character.isNull())charDye(character,e);}
  const look=character.isNull()?null:character.add(0x3c8).readPointer();
  if(look)log('Look probe char look skins='+look.add(0xc).readS32()+' dyes='+look.add(0x34).readS32());
  save('look-'+k+'-look.bin',encode(msg));
  log('Look probe saved scene '+k);
 }catch(e){log('Look probe error '+e+(e.context?' PC='+e.context.pc.sub(B):''));}
}});
log('Look probe installed');
