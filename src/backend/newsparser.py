from time import sleep
import requests as r
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from db import DB
from selenium.common.exceptions import WebDriverException

class RBCParser:
    def __init__(self, logger, scroll_cooldown, selenium_domain, selenium_port, db_creds):
        self.log = logger
        self.protocol = "https"
        self.site = "www.rbc.ru"
        self.SCROLL_COOLDOWN = scroll_cooldown
        # Connect to DB
        self.db = DB(db_creds)
        self.selenium_domain = selenium_domain
        self.selenium_port = selenium_port
        self.fetching = False

    def fetch(self, topic: str) -> bool:
        # If already fetching, quit
        if self.fetching:
            return False
        # Set the fetching flag
        self.fetching = True

        # Set up Selenium driver
        selenff_options = webdriver.FirefoxOptions()
        selenff_options.set_preference("http.response.timeout", 5)
        selenff_options.set_preference("dom.max_script_run_time", 5)
        #drv = webdriver.Remote("http://localhost:4444/wd/hub", options=selenff_options)  # Default port os 4444
        drv = webdriver.Remote(f"http://{self.selenium_domain}:{self.selenium_port}/wd/hub", options=selenff_options)

        # Load the webpage
        try:
            drv.get(self.protocol + "://" + self.site + "/" + topic)
        except WebDriverException:
            raise TimeoutError("Parser timed out")

        # Get more articles by scrolling down
        last_height = drv.execute_script("return document.body.scrollHeight")
        while True:
            # Scroll down to the bottom
            drv.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load more articles
            sleep(self.SCROLL_COOLDOWN)

            # Calculate new scroll height and compare with last scroll height
            new_height = drv.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Get page HTML source from Selenium driver
        html = drv.page_source

        # Parse page source with beautifulsoup
        soup = bs(html, features="html.parser")
        # Find all article links
        data = soup.findAll("a", {"class": "item__link"})

        # Placeholder for articles
        # Format:
        # {
            # "<ArticleID>": {
                # "title": "<Foo Bar fizz bazz>",
                # "preamble": "<Some intro text about Bar>",
                # "tldr": "<Short description of foo event>"
            # }
        # }
        articles = {}

        for news in data:
            news_link = news["href"]
            rncontent = r.get(news_link)
            ndata = bs(rncontent.text, features="html.parser")

            # Collect title
            title = ndata.find("h1").text.strip()

            # Collect preamble (it doesn't always exist!)
            try:
                preamble = ndata.find("div", {"class": "article__header__yandex"}).text.strip()
            except:
                preamble = None  # Sadness

            # Collect tldr (it also doesn't always exist!!)
            try:
                tldr = ndata.find("div", {"class": "article__text__overview"}).text.strip()
            except:
                tldr = None      # Also sadness

            # [DEBUG] Print article metadata
            # print("TITLE:", title)
            # print("PREAMBLE:", preamble)
            # print("TLDR:", tldr)

            # Parse all paragraphs
            paragraphs_raw = ndata.findAll("p")  # All (incl. empty and generally crappy) paragraphs
            paragraphs = []                      # Placeholder for clean paragraphs

            for i in range(len(paragraphs_raw)):
                if paragraphs_raw[i] is None:
                    continue  # Do not include a paragraph if it's NoneType
                if (paragraphs_raw[i].find("span", {"class": "article__inline-item__title"}) or
                    paragraphs_raw[i].find("span", {"class": "article__inline-item__title"})):
                    continue  # Skip inline article links

                stripped_paragraph = paragraphs_raw[i].text.strip()
                if stripped_paragraph == "":
                    continue  # Skip empty paragraphs
                # Else, include the paragraph
                paragraphs.append(stripped_paragraph)

            # [DEBUG] Print all paragraphs one by one
            #for par in paragraphs: print("PARAGRAPH:", par)

            # Construct the article's body from paragraphs (pr's may be used later!)
            body = ""
            for par in paragraphs:
                body += par + "\n"

            # If the article's body contains only video content, skip the article
            if body == "Video\n":
                continue

            # Construct the article's entry
            article = {"source": "rbc",
                       "topic": topic,
                       "title": title,
                       "preamble": preamble,
                       "tldr": tldr,
                       "body": body}

            # Add the atricle to articles
            articles[news_link.split("/")[-1]] = article

            # [DEBUG] Print the article's body
            #print(body)

            # Send article to db
            self.db.add_article(news_link.split("/")[-1], article)

        # Close the Selenium session
        try:
            drv.quit()
        except Exception as exc:
            print("Selenium failed on quit(). It probably already closed the session (Docker).\nException: {exc}")

        # Unset the fetching flag
        self.fetching = False
        return True


if __name__ == "__main__":
    from os import getenv
    from dotenv import load_dotenv
    load_dotenv()
    db_creds = {"user": getenv("DATACATS_PSQL_USER"),
                "pass": getenv("DATACATS_PSQL_PASS"),
                "host": getenv("DATACATS_PSQL_HOST"),
                "port": getenv("DATACATS_PSQL_PORT")}
    rbc = RBCParser(None,
                    2,
                    getenv("DATACATS_SELENIUM_DOMAIN"),
                    getenv("DATACATS_SELENIUM_PORT"),
                    db_creds)
    rbc.fetch("technology_and_media")
