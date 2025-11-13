# Database migration files

# Use Alembic for database migrations

# Initial schema creation

# Run: alembic revision --autogenerate -m "Initial schema"

# Then: alembic upgrade head

## Manual SQL Migrations

### 002_update_regions_urls.sql

기존 Supabase 데이터베이스의 regions 테이블을 업데이트하는 스크립트입니다.

**실행 방법:**

1. Supabase Dashboard → SQL Editor에서 실행
2. 또는 psql로 직접 실행:
   ```bash
   psql $DATABASE_URL -f database/migrations/002_update_regions_urls.sql
   ```

**업데이트 내용:**

- URL 형식: `https://jpcanada.com` → `https://bbs.jpcanada.com`
- bbs=4의 city를 Vancouver로 수정
- bbs=59 (Other Cities) 추가

**실행 후 확인:**

```sql
SELECT id, city, bbs, listing_url FROM regions ORDER BY bbs;
```
