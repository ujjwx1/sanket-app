import test from 'node:test'
import assert from 'node:assert/strict'
import { translations } from './i18n.js'

test('every supported interface language has all fixed labels', () => {
  const locales = ['hi', 'bn', 'gu', 'kn', 'ml', 'mr', 'pa', 'ta', 'te']
  const keys = Object.keys(translations.hi).sort()
  for (const locale of locales) {
    assert.deepEqual(Object.keys(translations[locale]).sort(), keys)
    for (const key of keys) assert.ok(translations[locale][key].trim(), `${locale}: ${key}`)
  }
})
