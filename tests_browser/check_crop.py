"""Real Croppr regression: resizing and dragging must remain on-image.

Run with .venv/bin/python tests_browser/check_crop.py after installing Chromium.
No server or real accounts are needed for this library/UI integration check.
"""
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def shrink_and_move_crop_left(page):
    image = page.locator('#crop-panel .croppr-image').bounding_box()
    handles = [handle.bounding_box() for handle in page.locator('#crop-panel .croppr-handle').all()]
    corner = max(handles, key=lambda box: box['x'] + box['y'])
    x = corner['x'] + corner['width'] / 2
    y = corner['y'] + corner['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x - image['height'] * 0.45, y - image['height'] * 0.45, steps=10)
    page.mouse.up()
    region = page.locator('#crop-panel .croppr-region').bounding_box()
    x = region['x'] + region['width'] / 2
    y = region['y'] + region['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(image['x'] + 1, y, steps=10)
    page.mouse.up()


def run():
    image = BytesIO()
    Image.new('RGB', (640, 480), '#c41230').save(image, 'PNG')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        page.set_content('''<style>img {max-width:400px} #crop-panel {width:400px}</style>
        <form id="profile-form"><input type="file" name="foto">
          <section id="crop-panel" hidden><img id="crop-source">
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
        original = page.evaluate('window.observedCrop.getValue("real")')
        shrink_and_move_crop_left(page)
        box = page.evaluate('window.observedCrop.getValue("real")')
        assert box['x'] < original['x'] and box['width'] < original['width'], box
        assert box['x'] >= 0 and box['y'] >= 0, box
        assert box['width'] >= 1 and box['height'] >= 1, box
        assert box['x'] + box['width'] <= 641 and box['y'] + box['height'] <= 481, box
        region = page.locator('#crop-panel .croppr-region')
        region.focus()
        before = page.evaluate('window.observedCrop.getValue("real")')
        region.press('ArrowRight')
        region.press('-')
        after = page.evaluate('window.observedCrop.getValue("real")')
        assert after['x'] > before['x'] and after['width'] < before['width'], (before, after)
        for _ in range(30):
            region.press('Shift+ArrowLeft')
            region.press('Shift+-')
        box = page.evaluate('window.observedCrop.getValue("real")')
        assert box['x'] >= 0 and box['width'] >= 1, box
        page.locator('#crop-apply').click()
        page.wait_for_function('!document.querySelector("#crop-preview-panel").hidden')
        assert page.locator('input[name=foto]').evaluate('(input) => input.files[0].size') > 0
        browser.close()
    print('Croppr: pointer movement, resize bounds and final file passed.')


if __name__ == '__main__':
    run()
