const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'custom_uploader/index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
// Load the limits actually passed by Python without starting the app or calling Gemini.
const limitsByCategory = JSON.parse(execFileSync('python3', ['-c', `
import ast,json
from pathlib import Path
module=ast.parse(Path('app.py').read_text())
assignment=next(n for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='UPLOAD_LIMITS' for t in n.targets))
print(json.dumps(eval(compile(ast.Expression(assignment.value),'app.py','eval'))))
`], {cwd: root, encoding: 'utf8'}));

function setup(limits, {width=100, height=100, broken=false, readFailure=false} = {}) {
  const elements = new Map(), messages = [], windowEvents = {}, documentEvents = {}, blobs = new Map();
  let reads = 0, decodes = 0, serial = 0;
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      open: false, showModal(){this.open=true;}, close(){this.open=false;this.events.close?.();}, style: {}, classList: {toggle(){},add(){},remove(){}}, events: {},
      addEventListener(name, fn){this.events[name]=fn;}, setAttribute(){}, focus(){}, click(){},
    });
    return elements.get(id);
  }
  const parent = {postMessage: m => messages.push(m)};
  const context = {
    window: {parent, addEventListener: (name, fn) => windowEvents[name]=fn},
    document: {
      body: {scrollHeight: 400}, documentElement: {style: {setProperty(){}}},
      getElementById: element, addEventListener: (name, fn) => documentEvents[name]=fn,
    },
    URL: {createObjectURL(file){const id=String(++serial);blobs.set(id,file);return id;},revokeObjectURL(id){blobs.delete(id);}},
    Image: class {
      set src(value){decodes++;this.naturalWidth=width;this.naturalHeight=height;
        queueMicrotask(()=>broken?this.onerror():this.onload());}
    },
    FileReader: class {
      readAsDataURL(){reads++;this.result='data:image/png;base64,dGVzdA==';
        queueMicrotask(()=>readFailure?this.onerror():this.onload());}
    },
    File: class {constructor(parts,name,options){Object.assign(this,parts[0],{name,type:options.type});}},
    setTimeout(){return 1;},clearTimeout(){},
  };
  vm.createContext(context);
  vm.runInContext(script,context);
  if(limits) windowEvents.message({source:parent,data:{type:'streamlit:render',args:{limits}}});
  return {
    context, element, documentEvents,
    values:()=>messages.filter(m=>m.type==='streamlit:setComponentValue'),
    error:()=>element('upload-dialog-message').textContent,
    title:()=>element('upload-dialog-title').textContent,
    close:()=>element('upload-dialog').close(),
    counts:()=>({reads,decodes,blobs:blobs.size}),
  };
}
const file = size => ({name:'test.png',type:'image/png',size});
for(const [category, limits] of Object.entries(limitsByCategory)) {
  test(`${category}: exact size and pixel boundaries accepted`,async()=>{
    const h=setup(limits,{width:limits.maxWidth,height:limits.maxHeight});
    await h.context.sendImage(file(limits.maxBytes));
    assert.equal(h.values().length,1);assert.equal(h.counts().blobs,0);
  });
  test(`${category}: excess byte rejected before base64 conversion or sending`,async()=>{
    const h=setup(limits);await h.context.sendImage(file(limits.maxBytes+1));
    assert.equal(h.values().length,0);assert.equal(h.counts().reads,0);assert.match(h.title(),/용량 제한 초과/);
  });
  for(const axis of ['width','height']) test(`${category}: excess ${axis} rejected before base64 conversion`,async()=>{
    const h=setup(limits,{width:limits.maxWidth,height:limits.maxHeight,[axis]:(axis==='width'?limits.maxWidth:limits.maxHeight)+1});
    await h.context.sendImage(file(100));
    assert.equal(h.values().length,0);assert.equal(h.counts().reads,0);assert.equal(h.counts().blobs,0);
    assert.match(h.title(),/크기/);
  });
}
test('thumbnail: non-square image rejected',async()=>{
  const h=setup(limitsByCategory['썸네일'],{width:499,height:500});
  await h.context.sendImage(file(100));assert.equal(h.values().length,0);assert.match(h.error(),/정방형/);
});
test('missing configuration blocks upload',async()=>{
  const h=setup(null);await h.context.sendImage(file(100));assert.equal(h.values().length,0);
});
for (const option of ['broken','readFailure']) test(`${option}: error allows retry without sending`,async()=>{
  const h=setup(limitsByCategory['팝업'],{[option]:true});
  await h.context.sendImage(file(100));h.close();await h.context.sendImage(file(100));
  assert.equal(h.values().length,0);assert.equal(h.counts().decodes,2);assert.equal(h.counts().blobs,0);assert.ok(h.error());
});
for (const route of ['select','drop']) test(`${route}: oversized file cannot be sent; valid retry succeeds`,async()=>{
  const limits=limitsByCategory['팝업'],h=setup(limits);
  async function trigger(f){
    if(route==='select') h.element('fileInput').events.change({target:{files:[f]}});
    if(route==='drop') h.element('uploader').events.drop({preventDefault(){},dataTransfer:{files:[f]}});
    await new Promise(resolve=>setImmediate(resolve));
  }
  await trigger(file(limits.maxBytes+1));assert.equal(h.values().length,0);
  h.close();await trigger(file(100));assert.equal(h.values().length,1);
});

test('clipboard paste has no handler or UI',()=>{
  const h=setup(limitsByCategory['팝업']);
  assert.equal(h.documentEvents.paste,undefined);
  assert.doesNotMatch(html,/클립보드|Ctrl\+V|upload-error/);
});
test('dimension-only rejection excludes size and repeated title from body',async()=>{
  const h=setup(limitsByCategory['팝업'],{width:521,height:801});
  await h.context.sendImage(file(2048));
  assert.equal(h.element('upload-dialog').open,true);
  assert.equal(h.title(),'이미지 크기 제한 초과');
  assert.match(h.error(),/허용 크기: 가로 520px · 세로 800px 이하/);
  assert.match(h.error(),/현재 크기: 가로 521px · 세로 801px/);
  assert.doesNotMatch(h.error(),/용량|제한 초과/);
  assert.equal(h.values().length,0);
});
test('size-only rejection excludes dimensions; rounding makes excess visible',async()=>{
  const h=setup(limitsByCategory['팝업']);
  await h.context.sendImage(file(512001));
  assert.equal(h.title(),'이미지 용량 제한 초과');
  assert.equal(h.error(),'허용 용량: 500KB 이하\n현재 용량: 500.01KB\n\n기준에 맞춰 이미지 수정 후 검사 수행 해주세요.');
  assert.equal(h.counts().reads,0);
});
test('combined rejection shows both failures without sending data',async()=>{
  const h=setup(limitsByCategory['팝업'],{width:600,height:900});
  await h.context.sendImage(file(600*1024));
  assert.equal(h.title(),'이미지 크기·용량 제한 초과');
  assert.match(h.error(),/현재 크기: 가로 600px · 세로 900px/);
  assert.match(h.error(),/현재 용량: 600.00KB/);
  assert.equal(h.values().length,0);
  assert.equal(h.counts().reads,0);
});
test('square-only rejection excludes passing dimensions and size limits',async()=>{
  const h=setup(limitsByCategory['썸네일'],{width:400,height:300});
  await h.context.sendImage(file(100));
  assert.equal(h.title(),'이미지 정방형 기준 미충족');
  assert.match(h.error(),/정방형/);
  assert.doesNotMatch(h.error(),/허용 크기|용량/);
});
test('thumbnail notice is separated into square, dimensions and size',()=>{
  const h=setup(limitsByCategory['썸네일']);
  assert.equal(h.element('limit-square').hidden,false);
  assert.equal(h.element('limit-dimensions').textContent,'가로·세로 500px 이하');
  assert.equal(h.element('limit-size').textContent,'200KB 이하');
  const popup=setup(limitsByCategory['팝업']);
  assert.equal(popup.element('limit-square').hidden,true);
});
test('unreadable oversized image still reports size violation',async()=>{
  const h=setup(limitsByCategory['팝업'],{broken:true});
  await h.context.sendImage(file(600*1024));
  assert.equal(h.title(),'이미지 용량 제한 초과');
  assert.match(h.error(),/현재 용량: 600.00KB/);
  assert.equal(h.values().length,0);
});
