from selenium.webdriver.common.by import By
from chrome_driver import setup_chrome_driver, wait_for_js_load
import logging
from collections import deque
from urllib.parse import urlparse
import urllib.robotparser
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_disallowed_urls(robots_url):
    rp = urllib.robotparser.RobotFileParser()
    
    response = requests.get(robots_url)
    
    if response.status_code != 200:
        logger.warning("Invalid response when querying for robots.txt from: ", robots_url)
        return []  # No file? skill issue, I crawl everything
    
    rp.parse(response.text.splitlines())
    
    disallowed_urls = [] 
    
    for path in rp.entries:
        if path.useragent != '*':  # For all User-agents
            with open("not_allowed_to_query.txt", "a") as f:
                f.write(robots_url + "\n")
            return [urlparse(robots_url).netloc] # return the domain since no urls are allowed
        for entry in path.disallow:
            disallowed_urls.append(entry)
    
    return disallowed_urls

def get_links(domain_url, driver, url_accept = lambda _: True):
    """
    Extract all unique links from the given domain.

    Args:
        domain_url (str): The starting URL of the domain to extract links from.
        driver (WebDriver): Selenium WebDriver instance used for web navigation.
        url_accept (callable, optional): A callback for accepting urls

    Yields:
        str: Extracted URLs from the domain.
    """
    if domain_url[-1] != "/": domain_url += "/"
    robots_path = domain_url + "robots.txt"
    disallowed_urls = get_disallowed_urls(robots_path)
    logger.info("Dissalowed urls: " + str(disallowed_urls))

    if domain_url in disallowed_urls:
        return ""
    
    visited = set(disallowed_urls)
    url_dq = deque([domain_url])

    while url_dq:
        for _ in range(len(url_dq)):
            url_node = url_dq.popleft()
            
            try:
                driver.get(url_node)
            except:
                continue
    
            if not wait_for_js_load(driver):
                logger.warning("Timeout for page: ", url_node)
                continue

            elements = driver.find_elements(By.TAG_NAME, "a")

            hrefs = [element.get_attribute("href") for element in elements]
            
            for href in hrefs:
                if not href: continue
                if href in visited: continue
                visited.add(href)
                
                if not url_accept(href): continue
                url_dq.append(href)

                yield href

if __name__ == "__main__":
    try:
        driver = setup_chrome_driver()
        domain_url = "https://fcim.utm.md/"
        base_domain = urlparse(domain_url).netloc
        logger.info(f"Base domain: {base_domain}")

        def url_accept_strategy(href):
            if urlparse(href).netloc != base_domain:
                logger.info(f"Not domain url: {href}")
                return False
            return True

        for link in get_links(domain_url, driver, url_accept_strategy):
            print(f"Found link: {link}")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        if 'driver' in locals():
            driver.quit()
