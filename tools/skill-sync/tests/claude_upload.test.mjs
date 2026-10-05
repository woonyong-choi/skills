// #37: 가짜 계정으로 영수증·description 판정과 재조회 실패 경계 검증
import assert from 'node:assert/strict';
import {mkdirSync, rmSync, statSync, chmodSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {join} from 'node:path';
import { test } from 'node:test';
import { planAccount, syncAccount, readReceipt, saveReceipt } from '../scripts/claude_upload.mjs';

const SKILL = {name:'alpha', description:'현재 설명', sourceHash:'tree', skillHash:'markdown', path:'alpha.zip'};
const PRESENT = {name:'alpha', description:'현재 설명', updatedAt:'today'};
const SAVED = {sourceHash:'tree', skillHash:'markdown', accountUpdatedAt:'today'};

for (const [label, saved, present, action] of [
  ['영수증 없음', undefined, PRESENT, '교체'],
  ['해시 다름', {...SAVED, sourceHash:'old'}, PRESENT, '교체'],
  ['description 다름', SAVED, {...PRESENT, description:'이전 설명'}, '교체'],
  ['같음', SAVED, PRESENT, undefined],
  ['계정 없음', SAVED, undefined, '업로드'],
  ['계정 변경', SAVED, {...PRESENT, updatedAt:'later'}, '교체'],
]) {
  test(`planAccount_${label}`, () => {
    const plan = planAccount([SKILL], present ? [present] : [], {version:1, skills:{alpha:saved}});
    assert.equal(plan[0]?.action, action);
  });
}

test('syncAccount_dry_run_reports_changes_without_upload_or_receipt', async () => {
  const receipt = {version:1, skills:{}};
  const before = JSON.stringify(receipt);
  const account = {list:async()=>[PRESENT, {name:'unmanaged'}], upload:async()=>assert.fail('dry-run upload')};
  const plan = await syncAccount([SKILL], account, receipt, ()=>assert.fail('dry-run save'), true);
  assert.equal(plan.length, 1);
  assert.equal(plan[0].name, 'alpha');
  assert.equal(JSON.stringify(receipt), before);
});

test('syncAccount_upload_then_requery_records_verified_hash', async () => {
  let rows = [{name:'unmanaged'}];
  const writes = [];
  const receipt = {version:1, skills:{}};
  const account = {list:async()=>rows, upload:async(item)=>{assert.equal(item.name,'alpha'); rows.push(PRESENT);}};
  await syncAccount([SKILL], account, receipt, value=>writes.push(structuredClone(value)), false);
  assert.equal(writes.length,2);
  assert.equal(writes[0].skills.alpha,undefined);
  assert.equal(writes[1].skills.alpha.sourceHash,'tree');
  assert.equal(writes[1].skills.alpha.description,'현재 설명');
  assert.ok(writes[1].skills.alpha.verifiedAt);
  assert.equal(rows[0].name,'unmanaged');
  const plan = await syncAccount([SKILL], account, receipt, ()=>assert.fail('unchanged save'), false);
  assert.deepEqual(plan, []);
});

for (const failure of ['upload', 'missing', 'description', 'final']) {
  test(`syncAccount_${failure}_fails_without_false_receipt`, async () => {
    const receipt = {version:1, skills:{alpha:{...SAVED,sourceHash:'old'}}};
    let calls = 0;
    const account = {
      list:async()=>{calls++; return calls === 1 || failure === 'final' && calls === 2 ? [PRESENT] : failure === 'description' ? [{...PRESENT,description:'wrong'}] : [];},
      upload:async()=>{if(failure === 'upload') throw Error('upload failed');},
    };
    await assert.rejects(syncAccount([SKILL],account,receipt,()=>{},false));
    if (failure !== 'final') assert.equal(receipt.skills.alpha, undefined);
  });
}

test('planAccount_duplicate_names_fails', () => {
  assert.throws(()=>planAccount([SKILL],[PRESENT,PRESENT],{version:1,skills:{}}), /duplicate/);
});

// #37: 영수증 파일은 원자 교체 후에도 600 권한 유지.
test('saveReceipt_roundtrip_and_permissions', () => {
  const root = fileURLToPath(new URL('../../../../.runtime/account-receipts/', import.meta.url));
  const folder = join(root, String(process.pid));
  const path = join(folder, 'receipt.json');
  mkdirSync(folder, {recursive:true});
  try {
    assert.deepEqual(readReceipt(path), {version:1,skills:{}});
    const receipt = {version:1,skills:{alpha:SAVED}};
    saveReceipt(receipt,path);
    assert.deepEqual(readReceipt(path),receipt);
    assert.equal(statSync(path).mode & 0o777,0o600);
    chmodSync(path,0o644);
    saveReceipt(receipt,path);
    assert.equal(statSync(path).mode & 0o777,0o600);
  } finally {rmSync(folder,{recursive:true});}
});
