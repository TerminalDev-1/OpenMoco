const root='/data/user/0/com.supercell.moco.localtest/files/diagnostics/';
function save(name, data) { const file=new File(root+name,'wb');file.write(data);file.close(); }
let own=null;
Interceptor.attach(owner.base.add(0x7245d8),{onEnter(args){log('Apartment frame destructor '+args[0]+' stack='+Thread.backtrace(this.context,Backtracer.ACCURATE).map(a=>a.sub(owner.base)).join(','));}});
Interceptor.attach(owner.base.add(0x786fdc),{onEnter(args){this.msg=args[0];},onLeave(){own=this.msg.add(0xa0).readPointer();}});
Interceptor.attach(owner.base.add(0x5bf784),{onEnter(args){
 const msg=args[1],scene=msg.add(0xa0).readPointer(),frame=scene.add(0x28).readPointer();
 try{
  const create=new NativeFunction(owner.base.add(0x8f0610),'pointer',['int']);
  const player=create(2009).sub(8);
  new NativeFunction(owner.base.add(0x735214),'void',['pointer','pointer','pointer'])(player,ptr(0),frame.add(0xc8).readPointer());
  const metadata=player.add(0x1e8).readPointer();metadata.writeU64(own.add(8).readU64());
  metadata.add(0x14).writeS32(1);metadata.add(0x20).writeS32(1);
  new NativeFunction(owner.base.add(0xa3934c),'void',['pointer','pointer'])(metadata.add(0x38),Memory.allocUtf8String('Local Hunter'));
  const registry=owner.base.add(0xfb8598).readPointer();
  const kit=new NativeFunction(owner.base.add(0x82ab0c),'pointer',['pointer','uint64'])(registry,6700000);
  metadata.add(0x1c0).writePointer(kit.sub(0x18)); metadata.add(0x1c8).writePointer(kit.sub(0x18));
  const runtimeScene=Memory.alloc(0x58); new NativeFunction(owner.base.add(0x7affa0),'void',['pointer','pointer'])(runtimeScene,registry); frame.add(0xb0).writePointer(runtimeScene);
  log('Apartment external before: frame='+frame+' context='+frame.add(0xc8).readPointer()+' playerFrame='+player.add(0x38).readPointer());
  save('frame-before.bin',frame.readByteArray(0x190));save('spawn-live-code.bin',owner.base.add(0x737bc0).readByteArray(0x140));
  try{ new NativeFunction(owner.base.add(0x7ac630),'void',['int','int','pointer','int','pointer'])(0,0,frame,1,player); log('Apartment external spawned character '+player.add(0xa8).readPointer()); const head=new NativeFunction(owner.base.add(0x82ab0c),'pointer',['pointer','uint64'])(registry,2900435); if(head.isNull())throw new Error('Known head cosmetic unavailable'); new NativeFunction(owner.base.add(0x6f2624),'void',['pointer','pointer'])(player.add(0xa8).readPointer(),head.sub(0x18)); log('Apartment applied loaded head cosmetic'); frame.add(0xb0).writePointer(ptr(0)); new NativeFunction(msg.readPointer().add(0x10).readPointer(),'void',['pointer'])(msg);const size=msg.add(0x1c).readS32();save('apartment-scene-body.bin',msg.add(0x40).readPointer().readByteArray(size));log('Apartment external saved '+size+' bytes'); }
  catch(e){log('Apartment external error '+e+' PC='+e.context.pc.sub(owner.base)+' x0='+e.context.x0);}
  log('Apartment external after: context='+frame.add(0xc8).readPointer());save('frame-after.bin',frame.readByteArray(0x190));
 } catch(e){log('Apartment external failed '+e);}
}});




