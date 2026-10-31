"""Streamlit integration checks using the repository's pinned runtime."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from streamlit.testing.v1 import AppTest
from gokpop_public.content import load_content


class ObservationAppTests(unittest.TestCase):
    def test_all_four_graphs_and_zoom_preserve_seven_records(self):
        before = (ROOT / 'data/public/site_data.json').read_bytes()
        app = AppTest.from_file(str(ROOT / 'main.py'), default_timeout=30).run()
        self.assertFalse(app.exception)
        for option in ['조회수', '좋아요', '강의 영상 점수', '종합지수 비교']:
            with self.subTest(metric=option):
                app.radio[0].set_value(option).run()
                self.assertFalse(app.exception)
                table = app.dataframe[0].value
                self.assertEqual(len(table), 7)
                self.assertEqual(list(table['관측일']), [
                    '2026-10-18', '2026-10-21', '2026-10-25', '2026-10-27',
                    '2026-10-28', '2026-10-29', '2026-10-31'])
                self.assertEqual(table.iloc[-1]['종합지수 비교'], '70.01')
                self.assertEqual(len(app.get('vega_lite_chart')), 1)
        app.checkbox[0].uncheck().run()
        self.assertFalse(app.exception)
        app.selectbox[0].set_value('2026-10-21').run()
        detail = '\n'.join(node.value for node in app.markdown)
        self.assertIn('2026-10-21', detail)
        self.assertIn('62,356', detail)
        self.assertIn('1,848', detail)
        self.assertEqual((ROOT / 'data/public/site_data.json').read_bytes(), before)

    def test_calculator_and_approved_note_still_work(self):
        before_history = (ROOT / 'data/public/lecture_history.json').read_bytes()
        app = AppTest.from_file(str(ROOT / 'main.py'), default_timeout=30).run()
        app.session_state['audience_menu'] = '직접 계산'
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input[0].value, '76716')
        self.assertEqual(app.text_input[1].value, '1901')
        app.button[0].click().run()
        self.assertFalse(app.exception)
        result_text = '\n'.join(node.value for node in app.markdown)
        self.assertIn('가상 결과', result_text)
        self.assertIn('70.01', result_text)
        app.text_input[0].set_value('80000')
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input[0].value, '80000')
        app.session_state['audience_menu'] = '감상 노트'
        app.run()
        self.assertFalse(app.exception)
        content = load_content(ROOT)
        paragraphs = '\n'.join(node.value for node in app.markdown)
        for text in content['audience_note']['paragraphs']:
            self.assertIn(text, paragraphs)
        self.assertIn('또 다른 댓글', paragraphs)
        self.assertEqual((ROOT / 'data/public/lecture_history.json').read_bytes(), before_history)
        self.assertEqual(len(content['records']), 1)


if __name__ == '__main__':
    unittest.main()
