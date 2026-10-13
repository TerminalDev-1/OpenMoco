const root='/data/user/0/com.supercell.moco.localtest/files/diagnostics/';
const create=new NativeFunction(owner.base.add(0x8f0610),'pointer',['int']);
Interceptor.attach(owner.base.add(0x5bf784),{onEnter(args){
 try{
 const msg=args[1],scene=msg.add(0xa0).readPointer(),frame=scene.add(0x28).readPointer();
 const portal=create(2010).sub(8);
 new NativeFunction(owner.base.add(0x732538),'void',['pointer','pointer','pointer'])(portal,ptr(0),frame.add(0xc8).readPointer());
 const path=Memory.alloc(16);new NativeFunction(owner.base.add(0xa3934c),'void',['pointer','pointer'])(path,Memory.allocUtf8String('sc3d/pf_keyitem_portal'));
 const manager=new NativeFunction(owner.base.add(0x8cb7a4),'pointer',[])();
 const type=new NativeFunction(owner.base.add(0x65d100),'pointer',[])();
 const stub=Memory.alloc(32);Memory.protect(stub,32,'rwx');stub.writeByteArray([0xe8,0x03,0x03,0xaa,0x50,0x00,0x00,0x58,0x00,0x02,0x1f,0xd6]);stub.add(12).writePointer(owner.base.add(0x8cb8f8));
 const out=Memory.alloc(16);new NativeFunction(stub,'void',['pointer','pointer','pointer','pointer'])(manager,type,path,out);if(out.readPointer().isNull())throw new Error('Portal asset reference unavailable');
 new NativeFunction(owner.base.add(0x86cdd4),'void',['pointer','pointer'])(portal.add(0x48),out);
 portal.add(0x70).writeS32(2);
 new NativeFunction(owner.base.add(0x72b840),'void',['pointer','int','int','int'])(portal,1500774,4561305,0);
 new NativeFunction(owner.base.add(0x728284),'void',['pointer','pointer'])(frame,portal);
 const buffer=new NativeFunction(owner.base.add(0xe771c0),'pointer',['uint64'])(65536);new NativeFunction(owner.base.add(0x8d7b2c),'void',['pointer','pointer','int'])(msg.add(8),buffer,65536);
 new NativeFunction(msg.readPointer().add(0x10).readPointer(),'void',['pointer'])(msg);
 const size=msg.add(0x1c).readS32(),file=new File(root+'portal-scene-body.bin','wb');file.write(msg.add(0x40).readPointer().readByteArray(size));file.close();log('Portal scene saved '+size+' bytes');
 }catch(error){log('Portal probe failed '+error);}
}});
