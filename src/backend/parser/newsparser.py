from time import sleep               # Handle DB connection failures
import requests as r                 # Request HTML
from bs4 import BeautifulSoup as bs  # Parse HTML
from selenium import webdriver
from db.alchemy import DB            # Connect to db
from selenium.common.exceptions import WebDriverException
from time import mktime
from datetime import datetime
from datetime import timedelta
from selenium.webdriver.common.by import By

# Selenium page interaction (used by RiaParser to wait for a clickable element)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class RiaParser:
    def __init__(self, logger, selenium_domain, selenium_port, db_creds, scroll_cooldown=3.7):
        self.log = logger
        self.protocol = "https"
        self.site = "ria.ru"
        self.SCROLL_COOLDOWN = scroll_cooldown
        # Connect to DB
        self.db = DB(db_creds)
        self.selenium_domain = selenium_domain
        self.selenium_port = selenium_port
        self.fetching = False

    def is_fetching(self) -> bool:
        return self.fetching

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
        drv = webdriver.Remote(f"http://{self.selenium_domain}:{self.selenium_port}/wd/hub", options=selenff_options)

        # Load the webpage
        try:
            drv.get(self.protocol + "://" + self.site + "/" + topic)
        except WebDriverException:
            raise TimeoutError("Parser timed out")

        # Select period "Timeframe/All"
        drv.find_element(By.CLASS_NAME, "list-date").click()
        drange = drv.find_element(By.CLASS_NAME, "date-range__ranges")
        drange.find_element(By.CSS_SELECTOR, 'li[data-range-days="all"]').click()

        # Scroll down to request more articles
        sleep(3)  # Wait for articles to load
        drv.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Click on the "x more articles" button
        try:
            list_more_btn = WebDriverWait(drv, 7).until(EC.presence_of_element_located((By.CLASS_NAME, "list-more")))
            list_more_btn.click()
        except Exception as exc:
            #! Enable logs in production
            #self.log.critical(f"\"Load more\" element not located. Exception message: {exc}")
            print(f"\"Load more\" element not located. Exception message: {exc}")

        # Get more articles by scrolling down
        first_attempt_failed = False
        last_height = drv.execute_script("return document.body.scrollHeight")
        while True:
            # Scroll down to the bottom
            drv.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load more articles
            sleep(self.SCROLL_COOLDOWN)

            # Calculate new scroll height and compare with last scroll height
            new_height = drv.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                if not first_attempt_failed:
                    sleep(15)
                    first_attempt_failed = True
                else:
                    first_attempt_failed = False
                    break
            last_height = new_height

        # Get page HTML source from Selenium driver
        html = drv.page_source

        # Parse page source with beautifulsoup
        soup = bs(html, features="html.parser")
        # Find all article links
        data = soup.findAll("a", {"class": "list-item__title color-font-hover-only"})

        # Placeholder for articles
        articles = {}

        for news in data:
            news_link = news["href"]
            rncontent = r.get(news_link)
            ndata = bs(rncontent.text, features="html.parser")

            # Collect title
            try:
                title = ndata.find("div", {"class": "article__title"}).text.strip()
            except AttributeError:
                try:
                    title = ndata.find("h1", {"class": "article__title"}).text.strip()
                except AttributeError:
                    continue

            # Collect preamble
            try:
                preamble = ndata.find("h1", {"class": "article__second-title"}).text.strip()
            except AttributeError:
                preamble = None

            # Collect tldr
            tldr = None

            # Collect timestamp
            timestamp = ndata.find("div", {"class": "article__info-date"})
            timestamp = datetime.strptime(timestamp.find("a").text, "%H:%M %d.%m.%Y")

            # Collect all paragraphs
            paragraphs_raw = ndata.findAll("div", {"class" :"article__text"})
            paragraphs = []

            for paragraph in paragraphs_raw:
                par_text = paragraph.text
                if par_text is None:
                    continue  # Do not include a paragraph if it's NoneType
                stripped_paragraph = par_text.strip()
                if stripped_paragraph == "":
                    continue  # Skip empty paragraphs
                # Else, include the paragraph
                paragraphs.append(stripped_paragraph)

            # Construct the article's body from paragraphs
            body = ""
            for par in paragraphs:
                body += par + "\n"

            # Construct the article's entry
            article = {"source": "ria",
                       "topic": topic,
                       "title": title,
                       "preamble": preamble,
                       "tldr": tldr,
                       "timestamp": timestamp,
                       "body": body}
            # Send article to db
            self.db.add_article("ria-"+news_link.split("/")[-1].split(".html")[0], article)

        # Close the Selenium session
        try:
            drv.quit()
        except Exception as exc:
            print("Selenium failed on quit(). It probably already closed the session (Docker).\nException: {exc}")

        # Unset the fetching flag
        self.fetching = False
        return True


class InvestingParser:
    def __init__(self, logger, selenium_domain, selenium_port, db_creds: dict, tz: int = -3):
        self.log = logger
        self.protocol = "https"
        self.site = "ru.investing.com"
        # Connect to DB
        self.db = DB(db_creds)
        self.selenium_domain = selenium_domain
        self.selenium_port = selenium_port
        self.fetching = False
        self.tz = tz

    def is_fetching(self) -> bool:
        return self.fetching

    def fetch(self, topic: str, pages: int = 100, start_page: int = 1) -> bool:
        # If already fetching, quit
        if self.fetching:
            return False
        # Set the fetching flag
        self.fetching = True

        # Set up Selenium driver
        selenff_options = webdriver.FirefoxOptions()
        selenff_options.set_preference("http.response.timeout", 5)
        selenff_options.set_preference("dom.max_script_run_time", 5)
        drv = webdriver.Remote(f"http://{self.selenium_domain}:{self.selenium_port}/wd/hub", options=selenff_options)

        # Load webpage `page` (iter)
        for page in range(start_page, start_page + pages):
            try:
                if page == 1:
                    drv.get(self.protocol + "://" + self.site + "/news/" + topic)
                else:
                    drv.get(self.protocol + "://" + self.site + "/news/" + topic + "/" + str(page))
            except WebDriverException:
                raise TimeoutError("Parser timed out")

            # Get page HTML source from Selenium driver
            html = drv.page_source

            # Parse page source with beautifulsoup
            soup = bs(html, features="html.parser")
            # Find all article links
            data = soup.findAll("a", {"class": "title"})

            for index, news in enumerate(data):
                # Parse every third index to reduce data volume
                #! You are expected to remove articles from this source before re-fetching!
                if index % 3 != 0:
                    continue
                news_link = news["href"]
                rncontent = r.get(self.protocol + "://" + self.site + news_link)
                ndata = bs(rncontent.text, features="html.parser")

                # Collect title
                try:
                    title = ndata.find("h1", {"class": "articleHeader"}).text.strip()
                except AttributeError:
                    title = None

                # Collect preamble
                preamble = None

                # Collect tldr
                tldr = None

                # Collect timestamp
                timestamp = ndata.find("div", {"class": "contentSectionDetails"}).find("span").text.strip()
                try:
                    timestamp = datetime.strptime(timestamp, "%d.%m.%Y %H:%M")
                except Exception as exc:
                    try:
                        timestamp = datetime.strptime(timestamp.split("(")[1][:-1], "%d.%m.%Y %H:%M")
                    except IndexError:
                        print(f"Index error on {timestamp}")
                timestamp -= timedelta(hours=self.tz)

                # Collect all paragraphs
                paragraphs = []
                paragraphs_raw = ndata.find("div", {"class": "WYSIWYG articlePage"})
                first_paragraph_raw = paragraphs_raw.findAll(text=True, recursive=False)
                first_paragraph = None
                for paragraph in first_paragraph_raw:
                    paragraph_strip = paragraph.strip()
                    if paragraph_strip == "":
                        continue
                    first_paragraph = paragraph_strip
                    break

                paragraphs_raw = paragraphs_raw.findAll("p")
                for paragraph in paragraphs_raw:
                    par_text = paragraph.text
                    if par_text is None:
                        continue  # Do not include a paragraph if it's NoneType
                    stripped_paragraph = par_text.strip()
                    if stripped_paragraph == "":
                        continue  # Skip empty paragraphs
                    # Else, include the paragraph
                    paragraphs.append(stripped_paragraph)

                # Construct the article's body from paragraphs
                if first_paragraph is not None:
                    body = first_paragraph + "\n"
                else:
                    body = ""
                for par in paragraphs:
                    body += par + "\n"

                # Construct the article's entry
                article = {"source": "investing",
                        "topic": topic,
                        "title": title,
                        "preamble": preamble,
                        "tldr": tldr,
                        "timestamp": timestamp,
                        "body": body}
                # Send article to db
                self.db.add_article("investing-" + news_link.split("/")[-1], article)

        # Close the Selenium session
        try:
            drv.quit()
        except Exception as exc:
            print("Selenium failed on quit(). It probably already closed the session (Docker).\nException: {exc}")

        # Unset the fetching flag
        self.fetching = False
        return True

class RBCParser:
    def __init__(self, logger, selenium_domain, selenium_port, db_creds, scroll_cooldown=0.7):
        self.log = logger
        self.protocol = "https"
        self.site = "www.rbc.ru"
        self.SCROLL_COOLDOWN = scroll_cooldown
        # Connect to DB
        self.db = DB(db_creds)
        self.selenium_domain = selenium_domain
        self.selenium_port = selenium_port
        self.fetching = False

    def is_fetching(self) -> bool:
        return self.fetching

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
                if not first_attempt_failed:
                    sleep(7)
                    first_attempt_failed = True
                else:
                    first_attempt_failed = False
                    break
            last_height = new_height

        # Get page HTML source from Selenium driver
        html = drv.page_source

        # Parse page source with beautifulsoup
        soup = bs(html, features="html.parser")
        # Find all article links
        data = soup.findAll("a", {"class": "item__link"})

        # Placeholder for articles
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

            # Collect timestamp
            pdatetime = ndata.find("time", {"class": "article__header__date"})["datetime"]
            tzdelta = pdatetime.split("+")[1].split(":")[0].lstrip("0")
            if pdatetime[19] == "-":
                tzdelta = -tzdelta
            timestamp = datetime.strptime(pdatetime.split("+")[0], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=-tzdelta)

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
                       "timestamp": timestamp,
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
                    0.7,
                    getenv("DATACATS_SELENIUM_DOMAIN"),
                    getenv("DATACATS_SELENIUM_PORT"),
                    db_creds)
    rbc.fetch("technology_and_media")
