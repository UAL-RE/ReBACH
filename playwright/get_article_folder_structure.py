import json
from playwright.sync_api import Playwright, sync_playwright, expect


def run(p: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True, channel='chromium')
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://arizona.figshare.com/articles/dataset/Optical_Phenotyping_Using_Label-Free_Microscopy_and_Deep_Learning/28664747/1")

    itemdatastr = ''
    for script in page.locator('//script').all():
        if script.inner_text().startswith(';(function() { window.__APOLLO_STATE__ = '):
            itemdatastr = script.inner_text()
            itemdatastr = itemdatastr.replace(';(function() { window.__APOLLO_STATE__ = ', '').replace('; }());', '')
            break

    itemdata = json.loads(itemdatastr)
    
    # find the key that contains the folder structure.
    filtered_keys = [key for key in itemdata.keys() if key.startswith('ItemVersion:')]
    if len(filtered_keys) != 1:
        raise Exception('More than one ItemVersion key found in item data structure on page ' + page.url)
    itemversiondata = itemdata[filtered_keys[0]]
    if not 'folderStructure' in itemversiondata.keys():
        raise Exception('folderStructure not found in item version data structure on page ' + page.url)
    folderstructure = itemversiondata['folderStructure']
    print(folderstructure)
    
    # ---------------------
    context.close()
    browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)