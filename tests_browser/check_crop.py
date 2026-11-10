"""Real Croppr regression: repeated keyboard adjustments must remain on-image.

Run with .venv/bin/python tests_browser/check_crop.py after installing Chromium.
No server or real accounts are needed for this library/UI integration check.
"""
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def run():
    image = BytesIO()
    Image.new('RGB', (640, 480), '#c41230').save(image, 'PNG')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        page.set_content('''<style>img {max-width:400px} #crop-panel {width:400px}</style>
        <form id="profile-form"><input type="file" name="foto">
          <section id="crop-panel" hidden><img id="crop-source">
            <button type="button" data-crop-move="left">Left</button>
            <button type="button" data-crop-move="right">Right</button>
            <button type="button" data-crop-move="up">Up</button>
            <button type="button" data-crop-move="down">Down</button>
            <button type="button" data-crop-scale="0.9">Shrink</button>
            <button type="button" data-crop-scale="1.1">Enlarge</button>
            <button type="button" id="crop-apply">Apply</button>
            <button type="button" id="crop-cancel">Cancel</button>
          </section><section id="crop-preview-panel" hidden><img id="crop-preview"></section>
          <p id="crop-status"></p><button id="profile-save">Save</button>
        </form>''')
        page.add_style_tag(path=str(ROOT / 'static/vendor/croppr-2.3.1.min.css'))
        page.add_script_tag(path=str(ROOT / 'static/vendor/croppr-2.3.1.min.js'))
        page.evaluate('''() => { const Original = window.Croppr;
          window.Croppr = function(...args) { window.observedCrop = new Original(...args); return window.observedCrop; };
        }''')
        page.add_script_tag(path=str(ROOT / 'static/sgr/perfil.js'))
        page.locator('input[name=foto]').set_input_files({'name': 'source.png', 'mimeType': 'image/png', 'buffer': image.getvalue()})
        page.wait_for_function('window.observedCrop && !document.querySelector("#crop-apply").disabled')
        page.locator('[data-crop-move=left]').press('Enter')
        for selector in ['[data-crop-move=left]', '[data-crop-move=up]', '[data-crop-move=right]', '[data-crop-move=down]', '[data-crop-scale="1.1"]', '[data-crop-scale="0.9"]']:
            page.locator(selector).evaluate('(button) => {for(let i=0;i<100;i++) button.click();}')
            box = page.evaluate('window.observedCrop.getValue("real")')
            assert box['x'] >= 0 and box['y'] >= 0, box
            assert box['width'] >= 1 and box['height'] >= 1, box
            assert box['x'] + box['width'] <= 641 and box['y'] + box['height'] <= 481, box
        page.locator('#crop-apply').click()
        page.wait_for_function('!document.querySelector("#crop-preview-panel").hidden')
        assert page.locator('input[name=foto]').evaluate('(input) => input.files[0].size') > 0
        browser.close()
    print('Croppr: keyboard bounds, minimum size and final file passed.')


if __name__ == '__main__':
    run()
