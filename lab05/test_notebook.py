"""Проверки сохранённого автономного ноутбука."""
import re
import unittest
from pathlib import Path

import nbformat


class NotebookTest(unittest.TestCase):
    def test_saved_outputs(self):
        notebook = nbformat.read(Path(__file__).parent / "eda.ipynb", 4)
        markdown = [c.source for c in notebook.cells if c.cell_type == "markdown"]
        figures = [s for s in markdown if "**Вопрос:**" in s]
        self.assertEqual(len(figures), 7)
        for text in figures:
            self.assertIn("**Результат:**", text)
            self.assertIn("**Решение:**", text)
        outputs = [o for c in notebook.cells if c.cell_type == "code"
                   for o in c.get("outputs", [])]
        self.assertFalse([o for o in outputs if o.output_type == "error"])
        self.assertEqual(sum("image/png" in o.get("data", {}) for o in outputs), 7)
        for output in outputs:
            text = "".join(output.get("data", {}).get("text/markdown", ""))
            self.assertFalse(re.search(r"\]\((?!https?://|#)[^)]+\)", text), text)
        self.assertTrue(all(c.execution_count is not None for c in notebook.cells
                            if c.cell_type == "code"))


if __name__ == "__main__":
    unittest.main()
