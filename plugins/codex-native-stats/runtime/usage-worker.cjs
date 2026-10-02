'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),readline=require('node:readline');
const {DatabaseSync}=require('node:sqlite'),{Stats}=require('./stats-core.cjs');
const {SpeedSamples}=require('./speed-samples.cjs');
const home=path.resolve(process.env.CODEX_HOME||path.join(os.homedir(),'.codex'));
const state=path.resolve(process.env.CODEX_STATS_PLUGIN_STATE||path.join(home,'plugins/state/codex-native-stats'));
const speeds=new SpeedSamples(path.join(state,'speed-samples.json'));
let database;const cache=new Map();
async function getStats(request){
  if(!request||typeof request.threadId!=='string'||!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(request.threadId))return {available:false,reason:'invalid-thread'};
  if(request.hostId&&request.hostId!=='local')return {available:false,reason:'remote-thread'};
  database ||= new DatabaseSync(path.join(home,'state_5.sqlite'),{readOnly:true});
  const row=database.prepare('SELECT id,rollout_path FROM threads WHERE id=?').get(request.threadId);
  if(!row)return {available:false,reason:'missing-thread'};
  const file=await fs.promises.realpath(row.rollout_path),base=await fs.promises.realpath(home),relative=path.relative(base,file);
  if(relative.startsWith('..')||path.isAbsolute(relative))return {available:false,reason:'external-rollout'};
  let stats=cache.get(row.id);
  if(!stats||stats.file!==file){stats=new Stats(file);cache.set(row.id,stats);}
  if(cache.size>8)cache.delete(cache.keys().next().value);
  try{await stats.update();}catch(e){if(e.message==='rollout-truncated')cache.delete(row.id);throw e;}
  return {available:true,threadId:row.id,...stats.snapshot(request.running===true),generation:speeds.snapshot(row.id,stats,request.streamSamples),collection:{state:'listening'}};
}
let queue=Promise.resolve();
readline.createInterface({input:process.stdin,crlfDelay:Infinity}).on('line',line=>{
  if(line.length>16384)return;
  queue=queue.then(async()=>{let message;try{message=JSON.parse(line);const result=message.enabled===false?{available:false,enabled:false,reason:'plugin-disabled'}:{enabled:true,...await getStats(message.request)};process.stdout.write(JSON.stringify({id:message.id,result})+'\n');}catch{process.stdout.write(JSON.stringify({id:message?.id,result:{available:false,enabled:message?.enabled!==false,reason:'local-record-unavailable'}})+'\n');}});
});
