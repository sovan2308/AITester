"""Two real Playwright tests against TTACart.

One passes, one is DESIGNED TO FAIL: it logs in with junk credentials and then
asserts it reached the products page. It never will. That permanent failure is
the point, it gives the retry graph something that stays red no matter how many
times you run it, so you can tell a flaky test from a genuinely broken one.
"""
import os
import re

from playwright.sync_api import Page, expect

URL = os.getenv("TTACART_URL", "https://app.thetestingacademy.com/playwright/ttacart/")

VALID_USER, VALID_PASS = "standard_user", "tta_secret"
BAD_USER, BAD_PASS = "not_a_user", "not_the_password"


def login(page: Page, username: str, password: str) -> None:
    page.goto(URL)
    page.locator("#user-name").fill(username)
    page.locator("#password").fill(password)
    page.locator("#login-button").click()


def test_valid_login(page: Page) -> None:
    """Correct credentials land on the products page. This one should pass."""
    login(page, VALID_USER, VALID_PASS)
    expect(page).to_have_url(re.compile(r"/inventory"))
    expect(page.get_by_text("Products")).to_be_visible()


def test_invalid_login(page: Page) -> None:
    """Wrong credentials. Asserting success here, so this ALWAYS fails."""
    login(page, BAD_USER, BAD_PASS)
    expect(page).to_have_url(re.compile(r"/inventory"))
