"""
Automatically remove N first videos from Youtube Watch Later playlist.

Usage:
    yt-remove-watch-later [-n NUMBER] [-c COOKIES]
    yt-remove-watch-later -h | --help
    yt-remove-watch-later --version

Options:
    -c COOKIES  Path to cookie file.
    -n NUMBER   Remove only N entries.
    -h, --help  Print this message.
    --version   Print version information.

Other considerations:

This program uses webscraping, because currently Youtube API cannot access
Watch Later Playlist.
"""

VERSION = '1.0'

from http.cookiejar import MozillaCookieJar

from docopt import docopt

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from ..config.youtube_scrapping import YoutubeScrappingConfigFile
from ..functional import compose, consume

import time
import os

from functools import partial

def spawn_driver(chrome_binary=None, chromedriver_binary=None):
    kwargs = {}

    if chrome_binary is not None:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.binary_location = chrome_binary

        kwargs['chrome_options'] = chrome_options

    if chromedriver_binary is not None:
        kwargs['executable_path'] = os.path.abspath(chromedriver_binary)

    return webdriver.Chrome(**kwargs)


def jar_cookie_to_webdriver_cookie(cookie):
    cookie_dict = {
        'domain': cookie.domain,
        'name': cookie.name,
        'value': cookie.value,
        'secure': cookie.secure
    }

    if cookie.expires:
        cookie_dict['expiry'] = cookie.expires

    if cookie.path_specified:
        cookie_dict['path'] = cookie.path

    return cookie_dict


def would_decorate_driver_with_cookies(driver, cookie_file):
    jar = MozillaCookieJar(cookie_file)
    jar.load()

    decorate = compose(
        driver.add_cookie,
        jar_cookie_to_webdriver_cookie
    )

    return map(decorate, jar)


def print_item_title(driver, elem):
    print(elem.get_attribute('data-title'))

    return elem


def click_single_delete_button(driver, elem):
    time.sleep(1)

    button = elem.find_elements_by_css_selector(".pl-video-edit-remove")

    driver.execute_script("arguments[0].click();", button[0])

    time.sleep(1)

    return elem


def would_click_delete_buttons(driver):
    elems = driver.find_elements_by_css_selector(".pl-video")

    print = partial(print_item_title, driver)
    delete = partial(click_single_delete_button, driver)

    return map(compose(delete, print), elems)


def main():
    arguments = docopt(__doc__, version=VERSION)

    conf = YoutubeScrappingConfigFile()

    driver = spawn_driver(
        chrome_binary=conf.chrome_binary,
        chromedriver_binary=conf.chromedriver_binary
    )

    # Required by cookies to be properly set
    driver.get("https://www.youtube.com")

    # Set cookies
    cookies = os.path.expanduser(arguments['-c'] or conf.cookies)

    consume(would_decorate_driver_with_cookies(
        driver,
        cookies
    ))

    driver.get("https://www.youtube.com/playlist?list=WL&disable_polymer=1")

    number = arguments['-n']
    if number:
        number = int(number)

    consume(would_click_delete_buttons(driver), number)
