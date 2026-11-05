import tempfile
import unittest
from pathlib import Path

import app


class ReportTests(unittest.TestCase):
    def test_loads_local_key_without_overriding_environment(self):
        import os
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            env_file = Path(folder) / '.env'
            env_file.write_text('GNANI_API_KEY=local-key\nLLM_MODEL=file-model\n', encoding='utf-8')
            with patch.dict(os.environ, {'LLM_MODEL': 'existing-model'}, clear=True):
                app.load_env(env_file)
                self.assertEqual(os.environ['GNANI_API_KEY'], 'local-key')
                self.assertEqual(os.environ['LLM_MODEL'], 'existing-model')

    def test_translation_preserves_original_and_validates_output(self):
        import io, json
        from unittest.mock import patch
        original = {'title': 'Original title', 'description': 'Original description', 'location': '', 'severity': 'high'}
        translated = {'title': 'Translated title', 'description': 'Translated description'}
        response = io.BytesIO(json.dumps({'choices': [{'message': {'content': json.dumps(translated)}}]}).encode())
        with patch.dict('os.environ', {'LLM_BASE_URL': 'https://example.test/v1', 'LLM_API_KEY': 'test', 'LLM_MODEL': 'test'}), patch('app.urlopen', return_value=response):
            result = app.translate_issue(original, 'en')
        self.assertEqual(result['title'], 'Translated title')
        self.assertEqual(result['location'], '')
        self.assertEqual(original['title'], 'Original title')
        self.assertNotIn('severity', result)

    def test_transcript_translation_supports_recording_languages(self):
        import io, json
        from unittest.mock import patch
        self.assertEqual(set(app.TRANSLATION_LANGUAGES), {'en', 'hi', 'bn', 'gu', 'kn', 'ml', 'mr', 'pa', 'ta', 'te'})
        response = io.BytesIO(json.dumps({'choices': [{'message': {'content': json.dumps({'title': 'Translated title', 'transcript': 'Translated transcript'})}}]}).encode())
        with patch.dict('os.environ', {'LLM_BASE_URL': 'https://example.test/v1', 'LLM_API_KEY': 'test', 'LLM_MODEL': 'test'}), patch('app.urlopen', return_value=response):
            result = app.translate_issue({'title': 'Original title'}, 'ta', transcript='Original transcript')
            self.assertEqual(result['title'], 'Translated title')
            self.assertEqual(result['transcript'], 'Translated transcript')

    def test_translation_rejects_unsupported_language(self):
        with self.assertRaises(ValueError):
            app.translate_issue({'title': 'Title'}, 'invalid')

    def test_report_persists_and_can_be_reviewed(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'reports.db'
            app.init_db(db)
            issue_id = app.save_issue(db, {'title': 'Broken guard', 'description': 'Guard is loose', 'severity': 'high'}, 'Guard is loose', None)
            self.assertEqual(app.get_issue(db, issue_id)['transcript'], 'Guard is loose')
            app.mark_reviewed(db, issue_id)
            self.assertEqual(app.get_issue(db, issue_id)['status'], 'reviewed')

    def test_rejects_missing_description(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'reports.db'
            app.init_db(db)
            with self.assertRaises(ValueError):
                app.save_issue(db, {'title': 'Issue', 'description': '', 'severity': 'unknown'}, 'text', None)

if __name__ == '__main__':
    unittest.main()
