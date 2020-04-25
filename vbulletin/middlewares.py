# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals
import logging
import cloudscraper

class CloudFlareMiddleware(object):
    """Scrapy middleware to bypass the CloudFlare's anti-bot protection"""
    logger = logging.getLogger(__name__)

    @staticmethod
    def is_cloudflare_challenge(response):
        """Test if the given response contains the cloudflare's anti-bot protection"""

        return (
                (response.status == 503 or response.status == 403)
                and response.headers.get('Server', '').startswith(b'cloudflare')
                and 'challenge' in response.text
        )

    def process_response(self, request, response, spider):
        """Handle the a Scrapy response"""

        if not self.is_cloudflare_challenge(response):
            return response


        self.logger.info(
            'Cloudflare protection detected on %s, trying to bypass...',
            response.url
        )

        if spider.settings.get("CAPTCHA_SOLVER"):
            cloudflare_tokens, __ = cloudscraper.get_tokens(
                request.url,
                browser={
                    'custom': spider.settings.get('USER_AGENT'),
                },
                recaptcha={
                    'provider': spider.settings.get('CAPTCHA_PROVIDER'),
                    'api_key': spider.settings.get('CAPTCHA_API_KEY'),
                }
            )
        else:
            cloudflare_tokens, __ = cloudscraper.get_tokens(
                request.url,
                browser={
                    'custom': spider.settings.get('USER_AGENT'),
                }
            )
        self.logger.info('Cloudflare tokens: %s', str(cloudflare_tokens))
        self.logger.info(
            'Successfully bypassed the protection for %s, re-scheduling the request',
            response.url
        )

        request.cookies.update(cloudflare_tokens)
        request.priority = 99999

        return request

class VbulletinSpiderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, dict or Item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request, dict
        # or Item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class VbulletinDownloaderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
