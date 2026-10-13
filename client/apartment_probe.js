const root='/data/user/0/com.supercell.moco.localtest/files/diagnostics/';
function save(name, data) { const file=new File(root+name,'wb');file.write(data);file.close(); }
let own=null;
function inspectHomeMap() {
 const bytes=File.readAllBytes('/data/user/0/com.supercell.moco.localtest/files/home.map_bin');
 const data=Memory.alloc(bytes.byteLength);data.writeByteArray(bytes);
 const stream=Memory.alloc(0x90);new NativeFunction(owner.base.add(0x8d6600),'void',['pointer','int'])(stream,0);
 new NativeFunction(owner.base.add(0x8d7b2c),'void',['pointer','pointer','int'])(stream,data,bytes.byteLength);
 const asset=new NativeFunction(owner.base.add(0x65ab3c),'pointer',[])();
 new NativeFunction(owner.base.add(0x866e00),'void',['pointer','pointer'])(asset,stream);
 const map=asset.add(0x30).readPointer();log('Decoded home map '+map);if(map.isNull())return;
 const vt=map.readPointer();log('Map vt='+vt.sub(owner.base)+' fields='+vt.add(0x18).readPointer().sub(owner.base));
 save('home-map-parsed.bin',map.readByteArray(0x1c0));for(const off of [0x50,0x60,0x70,0x80,0x90]){const vec=map.add(off),n=vec.add(12).readS32();if(n>0&&n<1000)save('map-vector-'+off.toString(16)+'.bin',vec.readPointer().readByteArray(n*(off===0x50?16:4)));}
 const names=Memory.alloc(16),grids=Memory.alloc(16);new NativeFunction(owner.base.add(0x7b90fc),'void',['pointer','pointer','pointer'])(map.add(0x28),names,grids);const layers=[];for(let i=0;i<names.add(12).readS32();i++){const s=names.readPointer().add(i*16),len=s.add(4).readS32(),name=len<8?s.add(8).readUtf8String(len):s.add(8).readPointer().readUtf8String(len),grid=grids.readPointer().add(i*8).readPointer();layers.push({name,grid:grid.toString(),bytes:Array.from(new Uint8Array(grid.readByteArray(64)))});save('home-grid-'+i+'.bin',grid.readByteArray(64));const n=grid.add(12).readS32();if(n>0&&n<100000)save('home-grid-data-'+i+'.bin',grid.readPointer().readByteArray(n*4));}File.writeAllText(root+'home-map-layers.json',JSON.stringify(layers)); const objCount=map.add(0x5c).readS32(),objNames=[];for(let i=0;i<objCount;i++){const s=map.add(0x50).readPointer().add(i*16),len=s.add(4).readS32();objNames.push({name:len<8?s.add(8).readUtf8String(len):s.add(8).readPointer().readUtf8String(len),x:map.add(0x60).readPointer().add(i*4).readS32(),y:map.add(0x70).readPointer().add(i*4).readS32()});}File.writeAllText(root+'home-map-objects.json',JSON.stringify(objNames));log('Home map objects '+JSON.stringify(objNames));const packed=grids.readPointer().readPointer().readPointer().readU32();const spawn={x:((packed&65535)<<16)|32768,y:((packed>>>16)<<16)|32768};log('Home spawn '+JSON.stringify(spawn));const count=map.add(0x13c).readS32();log('Home markers='+count);
 if(count>0&&count<1000){const a=map.add(0x130).readPointer(),rows=[];for(let i=0;i<count;i++){const p=a.add(i*8).readPointer();rows.push({index:i,bytes:Array.from(new Uint8Array(p.readByteArray(0x40)))});}File.writeAllText(root+'home-map-markers.json',JSON.stringify(rows));}return spawn;
}

Interceptor.attach(owner.base.add(0x786fdc),{onEnter(args){this.msg=args[0];},onLeave(){own=this.msg.add(0xa0).readPointer();}});
Interceptor.attach(owner.base.add(0x5bf784),{onEnter(args){
 const msg=args[1],scene=msg.add(0xa0).readPointer(),frame=scene.add(0x28).readPointer();
 try{
  const spawn=inspectHomeMap();
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
  try{ new NativeFunction(owner.base.add(0x7ac630),'void',['int','int','pointer','int','pointer'])(spawn.x,spawn.y,frame,1,player); log('Apartment external spawned character '+player.add(0xa8).readPointer()); const head=new NativeFunction(owner.base.add(0x82ab0c),'pointer',['pointer','uint64'])(registry,2900435); if(head.isNull())throw new Error('Known head cosmetic unavailable'); new NativeFunction(owner.base.add(0x6f2624),'void',['pointer','pointer'])(player.add(0xa8).readPointer(),head.sub(0x18)); log('Apartment applied loaded head cosmetic'); frame.add(0xb0).writePointer(ptr(0)); const outputBuffer=new NativeFunction(owner.base.add(0xe771c0),'pointer',['uint64'])(65536);new NativeFunction(owner.base.add(0x8d7b2c),'void',['pointer','pointer','int'])(msg.add(8),outputBuffer,65536);new NativeFunction(msg.readPointer().add(0x10).readPointer(),'void',['pointer'])(msg);const size=msg.add(0x1c).readS32();save('apartment-scene-body.bin',msg.add(0x40).readPointer().readByteArray(size));log('Apartment external saved '+size+' bytes'); }
  catch(e){log('Apartment external error '+e+' PC='+e.context.pc.sub(owner.base)+' x0='+e.context.x0);}
  log('Apartment external after: context='+frame.add(0xc8).readPointer());save('frame-after.bin',frame.readByteArray(0x190));
 } catch(e){log('Apartment external failed '+e);}
}});
