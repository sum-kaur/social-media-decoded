-- Development seed data — loads representative signals for all supported brands.
-- Usage: psql -U postgres -d social_media_decoded -f db/seed.sql

INSERT INTO signals (platform, brand, category, post_text, sentiment, signal_strength, engagements, author_handle, language)
VALUES
    -- Nike: mix of sentiment
    ('twitter',   'Nike', 'product_launch',  'Just copped the new Nike Air Max 2025. The cushioning is unreal. Worth every penny. #Nike #sneakers',                              'positive', 0.88, 245000, '@sneakerhead_jen', 'en'),
    ('instagram', 'Nike', 'ugc',             'Day 30 of training in my Nike React Infinity. Zero injuries. These shoes actually work.',                                           'positive', 0.92, 312000, '@runnerlife_k',    'en'),
    ('twitter',   'Nike', 'campaign',        'Nike''s new "Just Do It" campaign featuring local athletes is the most authentic thing they''ve done in years.',                  'positive', 0.75, 88000,  '@mktg_analyst',   'en'),
    ('tiktok',    'Nike', 'ugc',             'Tried to return these Nikes after the sole separated after 2 weeks. Customer service is a joke. Never again.',                    'negative', 0.45, 54000,  '@disappointed_dk', 'en'),
    ('reddit',    'Nike', 'product_launch',  'Nike quality has declined significantly since 2020. My Pegasus 40 delaminated after 3 months of normal use. QC is a problem.',    'negative', 0.38, 12000,  NULL,               'en'),
    ('twitter',   'Nike', 'sponsorship',     'Watching the Olympics and every athlete in Nikes looks incredible. The brand consistency is impressive.',                          'positive', 0.70, 67000,  '@olympics_fan',   'en'),

    -- Adidas: strong UGC and collab focus
    ('twitter',   'Adidas', 'collaboration', 'The Adidas x Pharrell collection just dropped and I''ve never bought something so fast. Fashion and function finally together.',    'positive', 0.95, 520000, '@style_forward',  'en'),
    ('instagram', 'Adidas', 'ugc',           'Running my 5th marathon in Adidas Adizero Boston 12. PR by 4 minutes. The shoe is doing work.',                                    'positive', 0.90, 445000, '@marathon_mama',  'en'),
    ('twitter',   'Adidas', 'product_launch','Adidas Ultraboost 24 review: comfortable for everyday wear but the midsole compresses quickly under heavy load. Mixed bag.',      'neutral',  0.62, 33000,  '@gear_reviewer',  'en'),
    ('tiktok',    'Adidas', 'ugc',           'POV: you just found an Adidas outlet and spent your entire paycheck. No regrets. #Adidas #haul',                                   'positive', 0.85, 680000, '@haul_queen',     'en'),
    ('reddit',    'Adidas', 'campaign',      'Adidas''s sustainability messaging feels genuine compared to competitors. Their Parley line uses real ocean plastic.',              'positive', 0.72, 28000,  NULL,              'en'),
    ('twitter',   'Adidas', 'collaboration', 'The Adidas x Bad Bunny collab sold out in 11 minutes. Their limited drops strategy is flawless.',                                  'positive', 0.88, 195000, '@streetwear_db',  'en'),

    -- Puma: smaller footprint, rising
    ('instagram', 'Puma', 'sponsorship',    'Puma''s partnership with NEYMAR JR is finally paying off. The boots are getting serious attention.',                                'positive', 0.65, 41000,  '@football_daily', 'en'),
    ('twitter',   'Puma', 'ugc',            'Puma Suede Classic never goes out of style. 50 years and it still slaps.',                                                          'positive', 0.78, 22000,  '@vintage_kicks',  'en'),
    ('tiktok',    'Puma', 'product_launch', 'Puma just quietly dropped the best running shoe of 2025 and nobody''s talking about it. The Velocity Nitro 3 is insane value.',    'positive', 0.81, 97000,  '@hidden_gems_run','en'),

    -- UnderArmour: performance-focused sentiment
    ('twitter',    'UnderArmour', 'campaign',      'Under Armour''s "The Only Way Is Through" campaign has no business being this motivating at 6am.',                          'positive', 0.74, 51000,  '@earlybird_ua',   'en'),
    ('instagram',  'UnderArmour', 'product_launch','Tested the UA HOVR Machina 3 for a full training cycle. Consistently responsive foam even after 400 miles.',               'positive', 0.80, 38000,  '@training_diary', 'en'),
    ('reddit',     'UnderArmour', 'ugc',           'Honest opinion: UA shirts are still the best moisture-wicking option at their price point. Nothing has beaten them.',       'positive', 0.68, 9500,   NULL,              'en'),

    -- NewBalance: community-driven momentum
    ('twitter',    'NewBalance', 'ugc',            'New Balance 990v6 is the shoe of the year and it''s not even close. Comfort on a different level.',                         'positive', 0.91, 172000, '@nb_forever',     'en'),
    ('instagram',  'NewBalance', 'collaboration',  'The New Balance x Aimé Leon Dore collab is proof that heritage brands can be just as hype as any Nike drop.',              'positive', 0.87, 263000, '@ald_fan',        'en'),
    ('tiktok',     'NewBalance', 'ugc',            'My dad wore New Balance his whole life. I laughed at him. Now I own 7 pairs. Full circle.',                                 'positive', 0.93, 1200000,'@gen_z_convert',  'en'),
    ('twitter',    'NewBalance', 'campaign',       'New Balance has quietly been making the most honest advertising in the industry. No gimmicks, just product.',               'positive', 0.76, 44000,  '@mktg_truth',     'en');
