import scrapy
import re
from vbulletin.processors import to_int
from vbulletin.items import PostItem, UserItem, ThreadItem
import logging


# This is a vBulletin forum, I wonder if all of them have similar XPath selection targets???

class VbulletinSpider(scrapy.Spider):
    name = 'vbulletin'

    patterns = {'thread_id': re.compile('\/(\d+)'),
    'next_page_url': "//*[@class='pagenav']//*[@href and contains(text(), '>')]/@href" }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        domain = getattr(self, "domain", None)
        url = getattr(self, "url", None)

        self.allowed_domains = [domain]
        self.start_urls = [url]

    def paginate(self, response, next_page_callback):
        """Returns a scrapy.Request for the next page, or returns None if no next page found.
        response should be the Response object of the current page."""
        # This gives you the href of the '>' button to go to the next page
        # There are two identical ones with the same XPath, so just extract_first.
        next_page = response.xpath(self.patterns['next_page_url'])

        if next_page:
            url = response.urljoin(next_page.extract_first())
            logging.info("NEXT PAGE IS: %s" % url)
            return scrapy.Request(url, next_page_callback)
        else:
            logging.info("NO MORE PAGES FOUND")
            return None

    def parse(self, response):
        # Parse the board (aka index) for forum URLs
        forum_urls = response.xpath('.//td[contains(@id,"f")]/div/a[not(contains(@href,"wiki"))]/@href').extract()
        for url in forum_urls:
            yield scrapy.Request(response.urljoin(url), callback=self.parse_forum)
            return

    def parse_forum(self, response):
        logging.info("STARTING NEW FORUM SCRAPE (GETTING THREADS)")
        thread_urls = response.xpath('.//a[contains(@id,"thread_title")]/@href').extract()
        for url in thread_urls:
            yield scrapy.Request(response.urljoin(url), callback=self.parse_posts)

        # return the next forum page if it exists
        yield self.paginate(response, next_page_callback=self.parse_forum)

    def parse_posts(self, response):
        logging.info("STARTING NEW PAGE SCRAPE")

        # Get info about thread
        # TODO: move this into parse_forum, b/c here the code runs every page of the thread
        thread = ThreadItem()
        try:
            thread['thread_id'] = to_int(re.findall(self.patterns['thread_id'], response.url)[0])
            # thread['thread_name'] = response.xpath('.//meta[@name="og:title"]/@content').extract_first()
            thread['thread_name'] = response.xpath('.//td[@class="navbar"]/strong/span[@itemprop="title"]/text()').extract_first()
            # thread['thread_path'] = response.xpath('.//div/table//tr/td/table//tr/td[3]//a/text()').extract()
            thread['thread_path'] = response.xpath('.//td/span[@itemscope="itemscope"]/span[@class="navbar"]/a/span[@itemprop="title"]/text()').extract()
            yield thread
        except Exception as e:
            self.logger.warning("Failed to extract thread data for thread: %s - error:\n %s", response.url, str(e))
            return

        # Scrape all the posts on a page for post & user info
        for post in response.xpath("//table[contains(@id,'post')]"):
            p = PostItem()

            p['thread_id'] = thread['thread_id']
            try:
                p['timestamp'] = post.xpath(".//tr/td[@style='font-weight:normal'][1]/text()").extract()[1].strip()

                p['message'] = post.xpath(".//*[contains(@id,'post_message_')]").extract()
                p['post_id'] = to_int(post.re_first('post\_message\_(\d+)'))

                # p['post_no'] = to_int(post.xpath(".//tr/td/div[@class='normal'][1]/a//text()").extract_first())
                p['post_no'] = to_int(post.xpath(".//a[contains(@id, 'postcount')]/@href").re_first('post(\d+)\.html'))
                yield p
            except Exception as e:
                self.logger.warning("Failed to extract post for thread: %s - exception: %s, args: %s", response.url, type(e).__name__, str(e.args))
                if "div-gpt-ad" not in post.get():
                    self.logger.warning("Response %s html:\n %s", response.url, post.get())
                continue

            try:
                p['user_id'] = to_int(post.xpath(".//a[@class='bigusername']/@href").re_first('\/(\d+)\.html'))
            except Exception as e:
                self.logger.warning("Failed to extract userid for thread: %s, post: %d - defaulting to -1", response.url, p['post_id'])
                p['user_id'] = -1

            # user info
            user = UserItem()
            try:
                user['user_id'] = p['user_id']
                user['user_name'] = post.xpath(".//a[@class='bigusername']//text()").extract_first()
                yield user
            except Exception as e:
                self.logger.warning("Failed to extract user info for thread: %s - error: %s\n", response.url, str(e))

        # Pagination across thread: search for the link that the next button '>' points to, if any
        # next_page_request = self.paginate(next_page_callback=self.parse_posts)
        # if next_page_request:
            # yield next_page_request
        # WARNING TODO just trying this, it might be None
        yield self.paginate(response, next_page_callback=self.parse_posts)

# Post container: use this for each post

# //table[contains(@id,'post')]

# Name (<a> with link to member page): ... /a[@class='bigusername']
# Get member page link URL with:
# ... a[@class='bigusername']/@href

# You could get name text with
# ... a[@class='bigusername']/text()
# you could also use userid to look up info later...

# Post messages:
# ... [contains(@id,'post_message_')]

