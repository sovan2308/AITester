"""Run test cases on TTACart with Playwright.

Test steps are written by an LLM, which is untrusted input. problems() only lets
through pages and data-test ids that really exist in TTACart, and goto can't
leave the app, so a confused (or prompt-injected) plan can't click around the web.
"""
import os
import re

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.getenv("TTA_URL", "https://app.thetestingacademy.com/playwright/ttacart/")
PRODUCTS = {  # id: (name, price) - read from TTACart's own ttacart.js
    "tta-practice-backpack": ("TTA Practice Backpack", 29.99),
    "tta-bike-light": ("TTA Bike Light", 9.99),
    "tta-bolt-tshirt": ("TTA Bolt T-Shirt", 15.99),
    "tta-fleece-jacket": ("TTA Fleece Jacket", 49.99),
    "tta-junior-tester-onesie": ("TTA Junior Tester Onesie", 7.99),
    "test-allthethings-tshirt-red": ("Test.allTheThings() T-Shirt (Red)", 15.99),
}
PAGES = {  # page: the data-test ids it renders ('' is the login page, <id> is a product id)
    "": "username password login-button error",
    "inventory.html": "title product-sort-container inventory-item-name inventory-item-price add-to-cart-<id> remove-<id>",
    "cart.html": "title cart-list inventory-item-name inventory-item-price item-quantity remove-<id> continue-shopping checkout",
    "checkout-step-one.html": "title firstName lastName postalCode continue cancel error",
    "checkout-step-two.html": "title inventory-item-name inventory-item-price subtotal-label tax-label total-label finish cancel",
    "checkout-complete.html": "title complete-header complete-text back-to-products",
    "item.html?id=<id>": "inventory-item-name inventory-item-desc inventory-item-price add-to-cart remove back-to-products",
}
AFTER_LOGIN = ("shopping-cart-link shopping-cart-badge open-menu close-menu inventory-sidebar-link "
               "reset-sidebar-link logout-sidebar-link")  # About and footer links leave the app, so they're out
IDS = {i.replace("<id>", pid) for ids in [*PAGES.values(), AFTER_LOGIN] for i in ids.split() for pid in PRODUCTS}
GOTO = {page.replace("<id>", pid) for page in PAGES for pid in PRODUCTS} | {"index.html"}


def problems(case):
    """Why a case can't run safely; [] means it can."""
    out = []
    for n, s in enumerate(case["steps"], 1):
        if s["do"] == "goto" and s["value"] not in GOTO:
            out.append(f"step {n}: '{s['value']}' is not a TTACart page")
        elif s["do"] not in ("goto", "url") and s["target"] not in IDS:
            out.append(f"step {n}: no element with data-test='{s['target']}'")
        elif s["do"] == "url" and not s["value"]:
            out.append(f"step {n}: url needs part of a url to look for")
        elif s["do"] == "count" and not s["value"].isdigit():
            out.append(f"step {n}: count needs a number, got '{s['value']}'")
    return out


def _do(page, base_url, s):
    el = page.locator(f'[data-test="{s["target"]}"]')
    match s["do"]:
        case "goto":   page.goto(base_url + s["value"])
        case "fill":   el.fill(s["value"])
        case "click":  el.first.click()
        case "select": el.select_option(s["value"])
        case "see":    expect(el.filter(has_text=s["value"]).first).to_be_visible()  # any match, not just the first
        case "not see": expect(el.filter(has_text=s["value"])).to_have_count(0)
        case "count":  expect(el).to_have_count(int(s["value"]))
        case "url":    expect(page).to_have_url(re.compile(re.escape(s["value"])))


def run(cases, out_dir, base_url=BASE_URL):
    """Each case gets a fresh browser context: logged out, empty cart."""
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for case in cases:
            page = browser.new_page()          # new_page() = new context; closing it clears state
            page.set_default_timeout(8000)     # performance_glitch_user logs in 4s late
            step = 0
            try:
                for step, s in enumerate(case["steps"], 1):
                    _do(page, base_url, s)
                results.append({**case, "status": "passed"})
            except Exception as exc:
                shot = out_dir / f"{case['id']}.png"
                page.screenshot(path=shot, full_page=True)
                lines = [l.strip() for l in str(exc).splitlines() if l.strip()] or [type(exc).__name__]
                error = " | ".join(lines[:1] + [l for l in lines if l.startswith("Actual value")][:1])
                # Playwright says "Actual value: None" when nothing matched; say it plainly for people and the LLM
                error = error.replace("Actual value: None", "no matching element on the page")
                error += f" | on page '{page.url.replace(base_url, '') or 'login'}'"
                results.append({**case, "status": "failed", "step": step, "error": error, "screenshot": str(shot)})
            page.close()
        browser.close()
    return results
