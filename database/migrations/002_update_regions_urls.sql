-- Update existing regions data to use correct JPCanada BBS URL format
-- 기존 regions 데이터의 URL을 올바른 형식으로 업데이트

-- 1. URL 형식 업데이트: https://jpcanada.com → https://bbs.jpcanada.com
UPDATE regions 
SET listing_url = REPLACE(listing_url, 'https://jpcanada.com/listing.php', 'https://bbs.jpcanada.com/listing.php')
WHERE listing_url LIKE '%jpcanada.com/listing.php%';

-- 2. www.jpcanada.com도 업데이트
UPDATE regions 
SET listing_url = REPLACE(listing_url, 'https://www.jpcanada.com/listing.php', 'https://bbs.jpcanada.com/listing.php')
WHERE listing_url LIKE '%www.jpcanada.com/listing.php%';

-- 3. bbs=4를 Vancouver로 업데이트 (기존에 Whistler로 잘못 설정된 경우)
UPDATE regions 
SET city = 'Vancouver'
WHERE bbs = 4 AND city != 'Vancouver';

-- 4. bbs=59 (Other Cities) 추가 (없는 경우에만)
INSERT INTO regions (city, bbs, listing_url, center)
SELECT 'Other Cities', 59, 'https://bbs.jpcanada.com/listing.php?bbs=59', ST_GeogFromText('POINT(-123.1207 49.2827)')
WHERE NOT EXISTS (SELECT 1 FROM regions WHERE bbs = 59);

-- 5. 결과 확인용 쿼리 (실행 후 확인)
-- SELECT id, city, bbs, listing_url FROM regions ORDER BY bbs;
