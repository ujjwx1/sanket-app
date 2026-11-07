import tempfile
import unittest
from pathlib import Path

import app


class ReportTests(unittest.TestCase):
    def test_speech_retries_temporary_connection_failure(self):
        import io, wave
        from urllib.error import URLError
        from unittest.mock import patch

        class Response(io.BytesIO):
            headers = {'Content-Type': 'audio/wav'}

        output = io.BytesIO()
        with wave.open(output, 'wb') as wav:
            wav.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            wav.writeframes(b'\x00\x00' * 100)
        with patch.dict('os.environ', {'GNANI_TTS_API_KEY': 'test'}), patch('app.time.sleep'), patch('app.urlopen', side_effect=[URLError('temporary'), Response(output.getvalue())]) as request:
            result = app.speak_translation('Hello', 'en')
        self.assertEqual(request.call_count, 2)
        with wave.open(io.BytesIO(result), 'rb') as wav:
            self.assertEqual(wav.getnframes(), 100)

    def test_speech_uses_separate_key_and_combines_audio(self):
        import io, json, wave
        from unittest.mock import patch

        class Response(io.BytesIO):
            headers = {'Content-Type': 'audio/wav'}

        def reply(request, timeout):
            self.assertEqual(request.get_header('X-api-key-id'), 'tts-key')
            payload = json.loads(request.data)
            self.assertEqual(payload['language'], 'pa-IN')
            self.assertLessEqual(len(payload['text']), 400)
            output = io.BytesIO()
            with wave.open(output, 'wb') as wav:
                wav.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                wav.writeframes(b'\x00\x00' * 100)
            return Response(output.getvalue())

        with patch.dict('os.environ', {'GNANI_TTS_API_KEY': 'tts-key'}), patch('app.urlopen', side_effect=reply) as mock:
            audio = app.speak_translation('word ' * 100, 'pa')
        self.assertEqual(mock.call_count, 2)
        with wave.open(io.BytesIO(audio), 'rb') as wav:
            self.assertEqual(wav.getnframes(), 200)

    def test_speech_requires_key_and_supported_language(self):
        from unittest.mock import patch
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'GNANI_TTS_API_KEY'):
                app.speak_translation('hello', 'en')
            with self.assertRaisesRegex(ValueError, 'supported speech language'):
                app.speak_translation('hello', 'invalid')

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

    def test_auto_transcription_requests_prisma_v3(self):
        import io, json
        from unittest.mock import patch
        response = io.BytesIO(json.dumps({'success': True, 'transcript': 'test'}).encode())
        with patch.dict('os.environ', {'GNANI_API_KEY': 'test'}), patch('app.urlopen', return_value=response) as mock_urlopen:
            self.assertEqual(app.transcribe(b'RIFFaudio', 'indic-auto'), 'test')
        request = mock_urlopen.call_args.args[0]
        self.assertIn(b'indic-auto', request.data)
        self.assertIn(b'prisma-v3.0', request.data)
        self.assertIn(b'RIFFaudio', request.data)

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
