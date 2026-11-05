import test from 'node:test'
import assert from 'node:assert/strict'
import { overview } from './overview.js'

test('counts only saved report statuses and severities', () => {
 const result = overview([{status:'new', data:{severity:'high'}, created_at:'2026-11-05T12:00:00Z'},{status:'reviewed',data:{severity:'unknown'},created_at:'2026-11-04T12:00:00Z'}], new Date('2026-11-06T12:00:00Z'))
 assert.equal(result.total,2); assert.equal(result.newCount,1); assert.equal(result.reviewed,1); assert.equal(result.highPriority,1); assert.equal(result.days.reduce((n,d)=>n+d.count,0),2)
})
