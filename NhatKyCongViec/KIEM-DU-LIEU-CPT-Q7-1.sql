-- KIEM-DU-LIEU-CPT-Q7-1.sql (11/11/2026) — CHI DOC (SELECT), thong ke tong hop, KHONG xuat dinh danh nguoi benh.
-- Danh cho DBA / chu du an co quyen. Ten bang/cot suy tu entity C#; chinh neu ten that khac.
-- Sua so voi ban trong tai lieu KQ: truy van F dung cot original_price / insurance_amount / final_price
-- (encounter_charges KHONG co cot total_amount).

-- A) Dot noi tru theo doi tuong thanh toan va co/khong gan the
SELECT a.payer_type, (a.health_insurance_card_id IS NOT NULL) AS co_the_gan_dot, COUNT(*) AS so_dot
FROM public.inpatient_admissions a WHERE a.status >= 0 GROUP BY 1, 2 ORDER BY 1, 2;

-- B) Dot BHYT co the het han trong thoi gian nam vien, nhom theo so ngay qua han (<= 15 / > 15 ngay)
SELECT CASE WHEN COALESCE(a.discharge_time::date, current_date) - c.valid_to <= 15 THEN 'het_han_trong_15_ngay'
            ELSE 'het_han_qua_15_ngay' END AS nhom_qua_han,
       COUNT(*) AS so_dot
FROM public.inpatient_admissions a
JOIN public.health_insurance_cards c ON c.id = a.health_insurance_card_id
WHERE a.status >= 0 AND a.payer_type = 1 AND c.valid_to < COALESCE(a.discharge_time::date, current_date)
GROUP BY 1;

-- B2) Dot BHYT vao vien khi the con han, het han giua dot (dung tinh huong an han noi tru)
SELECT COUNT(*) AS so_dot_het_han_giua_dot
FROM public.inpatient_admissions a
JOIN public.health_insurance_cards c ON c.id = a.health_insurance_card_id
WHERE a.status >= 0 AND a.payer_type = 1
  AND a.admitted_at::date <= c.valid_to
  AND c.valid_to < COALESCE(a.discharge_time::date, current_date);

-- C) Luot kham noi tru: payment_object_id / is_right_route / benefit_rate = 0 (ky vong nhieu dong 0/false do CompleteAdmission)
SELECT e.payment_object_id, e.is_right_route, (e.benefit_rate = 0) AS benefit_bang_0, COUNT(*) AS so_luot
FROM public.inpatient_admissions a JOIN public.encounters e ON e.id = a.encounter_id
WHERE a.status >= 0 GROUP BY 1, 2, 3 ORDER BY 4 DESC;

-- D) Lech muc huong giua the va luot kham cua cung dot (ca hai > 0)
SELECT c.benefit_level AS muc_the, e.benefit_rate AS muc_luot, COUNT(*) AS so_dot
FROM public.inpatient_admissions a
JOIN public.health_insurance_cards c ON c.id = a.health_insurance_card_id
JOIN public.encounters e ON e.id = a.encounter_id
WHERE a.status >= 0 AND c.benefit_level > 0 AND e.benefit_rate > 0 AND c.benefit_level <> e.benefit_rate
GROUP BY 1, 2 ORDER BY 3 DESC;

-- E) Dot BHYT gan the nhung the status <= 0, thieu muc huong, hoac loi ngay hieu luc
SELECT c.status,
       (c.benefit_level IS NULL OR c.benefit_level <= 0) AS thieu_muc_huong,
       (c.valid_from IS NULL OR c.valid_to IS NULL OR c.valid_from > c.valid_to) AS loi_ngay_hieu_luc,
       COUNT(*) AS so_dot
FROM public.inpatient_admissions a
JOIN public.health_insurance_cards c ON c.id = a.health_insurance_card_id
WHERE a.status >= 0 AND a.payer_type = 1
GROUP BY 1, 2, 3 ORDER BY 4 DESC;

-- E2) Dot BHYT khong gan the (muc huong chi co the lay tu du phong encounters.benefit_rate hoac khong co)
SELECT COUNT(*) AS so_dot_bhyt_khong_the
FROM public.inpatient_admissions a
WHERE a.status >= 0 AND a.payer_type = 1 AND a.health_insurance_card_id IS NULL;

-- F) (DA SUA) Khoan thu noi tru BHYT da ghi voi insurance_amount = 0 can tinh lai: so khoan va tong tien anh huong
SELECT COUNT(*) AS so_khoan_bhyt_bang_0,
       COALESCE(SUM(ec.original_price), 0) AS tong_gia_goc_anh_huong,
       COALESCE(SUM(ec.final_price), 0)    AS tong_nguoi_benh_phai_tra_anh_huong
FROM public.encounter_charges ec
WHERE ec.status >= 0
  AND ec.admission_id IS NOT NULL
  AND ec.payer_type = 1
  AND ec.insurance_amount = 0
  AND ec.original_price > 0;
