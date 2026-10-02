'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),vm=require('node:vm');
const {Stats}=require('../runtime/stats-core.cjs'),{SpeedSamples}=require('../runtime/speed-samples.cjs');
const file=path.join(os.homedir(),'AppData/Local/CodexStatsPlugin/validation','speed-test-'+process.pid+'.json');
let now=5000,listener;
const window={addEventListener:(type,fn)=>{listener=fn;},removeEventListener:()=>{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../runtime/speed-stream.js'),'utf8'),{window,Date:{now:()=>now},Map,Set});
const id='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222';
function notify(method,params,at,hostId='local'){now=at;listener({data:{type:'mcp-notification',hostId,method,params:{threadId:id,turnId:'one',...params}}});}
function start(itemId,at){notify('item/started',{item:{id:itemId,type:'reasoning'},startedAtMs:at},at);}
function complete(itemId,at){notify('item/completed',{item:{id:itemId,type:'reasoning'},completedAtMs:at},at);}
function usage(output,total,at){notify('thread/tokenUsage/updated',{tokenUsage:{last:{outputTokens:output},total:{outputTokens:total}}},at);}
function item(stats,itemId,kind,startMs,endMs,turn='one'){stats.accept({type:'event_msg',timestamp:new Date(endMs).toISOString(),payload:{type:'item_completed',turn_id:turn,item:{id:itemId,type:kind},started_at_ms:startMs,completed_at_ms:endMs}});}
function response(stats,responseId,out,endMs,turn='one'){stats.accept({type:'token_usage_record',timestamp:new Date(endMs).toISOString(),payload:{response_id:responseId,turn_id:turn,usage:{output_tokens:out}}});}
const stats=new Stats('');
start('a',10000);complete('a',11000);usage(600,600,15010);
item(stats,'a','Reasoning',10000,11000);item(stats,'tool-a','CommandExecution',11000,14000);item(stats,'tool-b','McpToolCall',12000,14500);response(stats,'r1',600,15000);
const store=new SpeedSamples(file);
let speed=store.snapshot(id,stats,window.__codexStatsSpeedStream.samples(id));
assert.equal(speed.latest,400);assert.equal(speed.samples,1);
usage(600,600,15500);assert.equal(window.__codexStatsSpeedStream.samples(id).length,1);
start('b',16000);complete('b',17000);usage(200,800,18010);
item(stats,'b','AgentMessage',16000,17000);response(stats,'r2',200,18000);
speed=store.snapshot(id,stats,window.__codexStatsSpeedStream.samples(id));
assert.equal(speed.latest,100);assert.equal(speed.samples,2);assert.ok(Math.abs(speed.mean-800/3.5)<1e-9);
assert.equal(store.snapshot(id,stats,window.__codexStatsSpeedStream.samples(id)).samples,2);
assert.equal(new SpeedSamples(file).snapshot(id,stats,[]).latest,100);
assert.equal(new SpeedSamples(file).snapshot(other,stats,[]).samples,0);
const count=window.__codexStatsSpeedStream.samples(id).length;
notify('item/started',{item:{id:'replay',type:'reasoning'},startedAtMs:4000},20000);complete('replay',20500);usage(10,810,21000);
assert.equal(window.__codexStatsSpeedStream.samples(id).length,count);
start('partial',22000);complete('unseen',22500);complete('partial',23000);usage(10,820,24000);
assert.equal(window.__codexStatsSpeedStream.samples(id).length,count);
start('abort',25000);notify('turn/completed',{},26000);usage(10,830,27000);
assert.equal(window.__codexStatsSpeedStream.samples(id).length,count);
const bad={turnId:'one',startMs:10000,observedEndMs:15010,firstItemId:'a',outputTokens:601};
assert.equal(new SpeedSamples(file+'.mismatch').snapshot(id,stats,[bad]).samples,0);
assert.equal(new SpeedSamples(file+'.wrong-turn').snapshot(id,stats,[{...bad,turnId:'other',outputTokens:600}]).samples,0);
assert.equal(new SpeedSamples(file+'.multiple').snapshot(id,stats,[{...bad,outputTokens:600,observedEndMs:19000}]).samples,0);
const mid=new Stats('');item(mid,'unseen','Reasoning',19000,20000);item(mid,'seen','AgentMessage',21000,22000);response(mid,'r3',100,23000);
assert.equal(new SpeedSamples(file+'.midstream').snapshot(id,mid,[{turnId:'one',startMs:21000,observedEndMs:23010,firstItemId:'seen',outputTokens:100}]).samples,0);
const concurrent=new Stats('');item(concurrent,'m','AgentMessage',30000,34000);item(concurrent,'t','CommandExecution',32000,35000);response(concurrent,'r4',400,35000);
assert.equal(new SpeedSamples(file+'.concurrent').snapshot(id,concurrent,[{turnId:'one',startMs:30000,observedEndMs:35010,firstItemId:'m',outputTokens:400}]).latest,100);
console.log(JSON.stringify({passed:true,checks:['native-event-pairing','exclude-overlapping-tools','weighted-mean','duplicates','persistence','thread-isolation','replay','partial','aborted','mismatched-usage','ambiguous-response']}));
