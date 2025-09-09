import json
from playwright.sync_api import Playwright, sync_playwright


def run(p: Playwright) -> None:
    browser = p.chromium.launch(headless=True, channel='chromium')
    context = browser.new_context()
    page = context.new_page()
    page.goto(
        "https://arizona.figshare.com/articles/dataset/"
        + "Supplementary_Information_for_The_Journey_of_Sediment-Rich_M_langes_in_Subduction_Zones_Table_S1_to_S12/27989354/1"
    )

    itemdatastr = ''
    for script in page.locator('//script').all():
        if script.inner_text().startswith(';(function() { window.__APOLLO_STATE__ = '):
            itemdatastr = script.inner_text()
            itemdatastr = itemdatastr.replace(';(function() { window.__APOLLO_STATE__ = ', '').replace('; }());', '')
            break

    itemdata = json.loads(itemdatastr)
    print(itemdatastr)

    # find the key that contains the folder structure.
    filtered_keys = [key for key in itemdata.keys() if key.startswith('ItemVersion:')]
    for key in filtered_keys:
        itemversiondata = itemdata[key]
        if 'folderStructure' in itemversiondata.keys():
            folderstructure = itemversiondata['folderStructure']
        else:
            folderstructure = {}
        print(f'Item Version {key.split(':')[-1].replace('}', '')}\n---------')
        print(folderstructure)

    # ---------------------
    context.close()
    browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
