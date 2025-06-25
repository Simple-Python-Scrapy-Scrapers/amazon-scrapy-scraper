import scrapy
from urllib.parse import urljoin

class AmazonSearchSpider(scrapy.Spider):
    name = "amazon_search"

    custom_settings = {
        'FEEDS': { 'data/%(name)s_%(time)s.csv': { 'format': 'csv',}}
        }

    def start_requests(self):
        keyword_list = ['ipad']
        for keyword in keyword_list:
            amazon_search_url = f'https://www.amazon.com/s?k={keyword}&page=1'
            yield scrapy.Request(url=amazon_search_url, callback=self.parse_search_results, meta={'keyword': keyword, 'page': 1})

    def parse_search_results(self, response):
        page = response.meta['page']
        keyword = response.meta['keyword'] 

        ## Extract Overview Product Data
        search_products = response.css("div.s-result-item")
        for product in search_products:
            # Try multiple title selectors (from old spider)
            title = (
                product.css("h2 a span::text").get() or
                product.css("h2 span::text").get() or
                product.css("a.a-link-normal span::text").get()
            )
            
            # Try multiple URL selectors (from old spider)
            relative_url = (
                product.css("h2 a::attr(href)").get() or
                product.css("a.a-link-normal::attr(href)").get()
            )
            
            if relative_url and title:  # Check if both URL and title exist
                asin = relative_url.split('/')[3] if len(relative_url.split('/')) >= 4 else None
                product_url = urljoin('https://www.amazon.com/', relative_url).split("?")[0]
                
                # Price selectors (from old spider)
                price_whole = product.css("span.a-price-whole::text").get()
                price_frac = product.css("span.a-price-fraction::text").get()
                price = f"{price_whole}.{price_frac}" if price_whole and price_frac else price_whole or "N/A"
                
                # Rating selector (from old spider)
                rating = product.css("span.a-icon-alt::text").get()
                
                yield {
                    "keyword": keyword,
                    "asin": asin,
                    "url": product_url,
                    "ad": True if "/slredirect/" in product_url else False, 
                    "title": title.strip(),
                    "price": price,
                    "rating": rating.strip() if rating else None,
                    "rating_count": product.css("span[aria-label~=stars] + span::attr(aria-label)").get(),
                    "thumbnail_url": product.xpath("//img[has-class('s-image')]/@src").get(),
                }


        ## Get All Pages
        if page == 1:
            available_pages = response.xpath(
                '//*[contains(@class, "s-pagination-item")][not(has-class("s-pagination-separator"))]/text()'
            ).getall()

            if available_pages:
                last_page = available_pages[-1]
                for page_num in range(2, int(last_page)):
                    amazon_search_url = f'https://www.amazon.com/s?k={keyword}&page={page_num}'
                    yield scrapy.Request(url=amazon_search_url, callback=self.parse_search_results, meta={'keyword': keyword, 'page': page_num}) 