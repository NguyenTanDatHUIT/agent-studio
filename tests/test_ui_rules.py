"""Static guards for docs/UI-RULES.md: every form control follows the template, not browser defaults."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / 'agent_orchestrator' / 'web_assets'
CSS = (ASSETS / 'style.css').read_text(encoding='utf-8')
RULE = re.compile(r'([^{}]+)\{([^{}]*)\}')
CSS_CLEAN = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)
BACKGROUND_SHORTHAND = re.compile(r'(?<![-\w])background\s*:')


def rules():
    for selector, body in RULE.findall(CSS_CLEAN):
        yield selector.strip(), body


class FormControlRules(unittest.TestCase):
    def test_global_rule_covers_input_select_textarea_with_template_tokens(self):
        block = [body for sel, body in rules() if sel.startswith('#ao-studio :where(input:not(') and 'textarea' in sel]
        self.assertEqual(len(block), 1, 'missing the global form-control rule (see docs/UI-RULES.md)')
        body = block[0]
        for needle in ('appearance:none', 'var(--ao-text)', 'var(--ao-panel)', 'var(--ao-line)', 'border-radius'):
            self.assertIn(needle, body)
        self.assertRegex(CSS, r'accent-color:var\(--ao-accent\)')  # checkbox / radio

    def test_select_keeps_its_arrow_even_when_a_component_sets_background(self):
        arrow = [body for sel, body in rules() if sel == '#ao-studio select:not([multiple]):not([size])']
        self.assertEqual(len(arrow), 1)
        self.assertIn('background-image:url(', arrow[0])
        self.assertIn('!important', arrow[0])

    def test_component_rules_for_select_never_use_background_shorthand(self):
        offenders = [sel for sel, body in rules()
                     if ':where(' not in sel and re.search(r'(^|[\s,>+~])select\b', sel)
                     and BACKGROUND_SHORTHAND.search(body)]
        self.assertEqual(offenders, [], 'use background-color on a select, the shorthand erases the arrow')

    def test_components_do_not_redeclare_the_control_look(self):
        # Class rules aimed at a form control may only lay it out; look comes from the global rule.
        # Exceptions are documented in docs/UI-RULES.md (borderless terminal prompt, compact layout cell).
        allowed = ('.ao-command-input', '.ao-layout-input')
        look = re.compile(r'(?<![-\w])(border|border-color|border-radius|background|background-color|color)\s*:')
        offenders = []
        for sel, body in rules():
            if sel.startswith('@') or ':where(' in sel or any(a in sel for a in allowed):
                continue
            if re.search(r'(^|[\s,>+~])(select|textarea)\b', sel) or re.search(
                    r'(ao-field|ao-filter|ao-history-search|ao-window-dialog)\s+(input|select|textarea)\b|\.ao-filter\b|\.ao-history-search\b', sel):
                if look.search(body):
                    offenders.append(sel)
        self.assertEqual(offenders, [], 'drop the look from these rules, the global form-control rule already styles them')

    def test_select_popup_is_the_template_menu_not_the_native_one(self):
        js = (ASSETS / 'app.js').read_text(encoding='utf-8')
        for needle in ('function openSelectMenu', 'data-select-menu', "addEventListener('mousedown'", 'event.preventDefault();sel.focus();openSelectMenu(sel)'):
            self.assertIn(needle, js)
        for cls in ('.ao-select-menu', '.ao-select-option'):
            self.assertTrue(any(cls in sel for sel, _ in rules()), f'missing CSS for {cls}')

    def test_terminal_windows_are_rebuilt_when_a_resumed_session_reuses_the_id(self):
        js = (ASSETS / 'app.js').read_text(encoding='utf-8')
        self.assertIn('old.gen!==s.gen', js)
        self.assertIn('gen:info.gen', js)

    def test_a_closed_dialog_is_always_hidden(self):
        # Regression: .ao-transcript-dialog{display:flex} beat the default dialog:not([open]){display:none}, so the closed
        # transcript viewer showed up as a 640px block at the bottom of the page.
        guard = [body for sel, body in rules() if sel == '#ao-studio dialog:not([open])']
        self.assertEqual(len(guard), 1, 'missing the rule that hides closed dialogs')
        self.assertIn('display:none', guard[0].replace(' ', ''))
        # a class rule that sets display on a dialog is only safe because the guard above is more specific
        class_rule = re.compile(r'^#ao-studio \.[\w-]*dialog[\w-]*$')
        for sel, body in rules():
            if class_rule.match(sel) and re.search(r'(?<![-\w])display\s*:', body):
                specificity_ok = '#ao-studio dialog:not([open])'  # (1,1,1) beats (1,1,0)
                self.assertIn(specificity_ok, [s for s, _ in rules()])

    def test_no_inline_styles_on_form_controls_in_templates(self):
        pattern = re.compile(r'<(?:input|select|textarea)\b[^>]*\bstyle\s*=', re.I)
        for name in ('index.html', 'app.js'):
            text = (ASSETS / name).read_text(encoding='utf-8')
            self.assertEqual(pattern.findall(text), [], f'{name}: style the control through CSS tokens, not inline')


if __name__ == '__main__':
    unittest.main()
