DO $$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_database
      WHERE datname = 'sazman'
   ) THEN
      CREATE DATABASE sazman;
   END IF;
END $$;
