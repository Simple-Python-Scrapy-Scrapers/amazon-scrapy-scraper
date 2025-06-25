import json
import scrapy
from urllib.parse import urljoin
import re

class AmazonProductSpider(scrapy.Spider):
    name = "amazon_product"

    custom_settings = {
        'FEEDS': { 'data/%(name)s_%(time)s.csv': { 'format': 'csv',}}
        }

    def start_requests(self):
        keyword_list = ['ipad']
        for keyword in keyword_list:
            amazon_search_url = f'https://www.amazon.com/s?k={keyword}&page=1'
            yield scrapy.Request(url=amazon_search_url, callback=self.discover_product_urls, meta={'keyword': keyword, 'page': 1})

    def discover_product_urls(self, response):
        page = response.meta['page']
        keyword = response.meta['keyword'] 

        ## Discover Product URLs
        search_products = response.css("div.s-result-item")
        for product in search_products:
            # Try multiple URL selectors (from old spider)
            relative_url = (
                product.css("h2 a::attr(href)").get() or
                product.css("a.a-link-normal::attr(href)").get()
            )
            
            if relative_url:  # Check if relative_url is not None
                product_url = urljoin('https://www.amazon.com/', relative_url).split("?")[0]
                yield scrapy.Request(url=product_url, callback=self.parse_product_data, meta={'keyword': keyword, 'page': page})
            
        ## Get All Pages
        if page == 1:
            available_pages = response.xpath(
                '//*[contains(@class, "s-pagination-item")][not(has-class("s-pagination-separator"))]/text()'
            ).getall()

            if available_pages:
                last_page = available_pages[-1]
                for page_num in range(2, int(last_page)):
                    amazon_search_url = f'https://www.amazon.com/s?k={keyword}&page={page_num}'
                    yield scrapy.Request(url=amazon_search_url, callback=self.discover_product_urls, meta={'keyword': keyword, 'page': page_num})


    def parse_product_data(self, response):
        try:
            image_data = json.loads(re.findall(r"colorImages':.*'initial':\s*(\[.+?\])},\n", response.text)[0])
        except (IndexError, json.JSONDecodeError):
            image_data = []
            
        try:
            variant_data = re.findall(r'dimensionValuesDisplayData"\s*:\s* ({.+?}),\n', response.text)
        except:
            variant_data = []
            
        feature_bullets = [bullet.strip() for bullet in response.css("#feature-bullets li ::text").getall()]
        
        # Price selectors (from old spider)
        price_whole = response.css("span.a-price-whole::text").get()
        price_frac = response.css("span.a-price-fraction::text").get()
        price = f"{price_whole}.{price_frac}" if price_whole and price_frac else price_whole or "N/A"
        
        # Rating selector (from old spider)
        rating = response.css("span.a-icon-alt::text").get()
        
        yield {
            "name": response.css("#productTitle::text").get("").strip(),
            "price": price,
            "stars": rating.strip() if rating else "",
            "rating_count": response.css("div[data-hook=total-review-count] ::text").get("").strip(),
            "feature_bullets": feature_bullets,
            "images": image_data,
            "variant_data": variant_data,
        } 