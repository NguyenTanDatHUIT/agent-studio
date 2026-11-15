-- KIEM-DON-VI-GIA-THUOC.sql  (11/11/2026) — CHI DOC, khong sua du lieu. Danh cho DBA / Khoa Duoc.
-- Muc dich (cau 3 cua E6b): xac nhan drug_price_items.price dang tinh theo DON VI CO SO (vien, ong, lo, chai, tui)
-- chu khong phai theo hop/thung, TRUOC khi chay E6b dot 2 (ghi khoan thu khi phat thuoc).
-- Luu y: ten bang/cot suy tu entity C# (DrugPriceItem, DrugCatalog, InventoryItem); DBA dieu chinh neu ten that khac.
-- Khong dua ket qua nay vao ma; ket qua chi de nguoi co tham quyen (Khoa Duoc) ket luan.

-- 1) Thuoc co gia tai thoi diem hien tai va so sanh voi gia tham khao + gia ban/gia von cua lo ton kho.
--    ty_le_so_voi_tham_khao >> 1 hoac << 1 goi y gia dang luu theo don vi lon hon/nho hon don vi co so.
WITH gia_hieu_luc AS (
  SELECT p.drug_catalog_id, p.price_type_id, p.price, p.effective_from, p.effective_to,
         ROW_NUMBER() OVER (PARTITION BY p.drug_catalog_id, p.price_type_id
                            ORDER BY p.effective_from DESC, p.id DESC) AS rn
  FROM public.drug_price_items p
  WHERE p.status >= 0
    AND p.drug_catalog_id IS NOT NULL
    AND p.effective_from <= now()
    AND (p.effective_to IS NULL OR p.effective_to >= now())
),
lo_ton AS (
  SELECT i.drug_catalog_id,
         MIN(i.unit_cost_price)                                  AS gia_von_min,
         MAX(i.unit_cost_price)                                  AS gia_von_max,
         MIN(COALESCE(i.unit_selling_price_override, i.unit_cost_price)) AS gia_ban_lo_min,
         MAX(COALESCE(i.unit_selling_price_override, i.unit_cost_price)) AS gia_ban_lo_max
  FROM public.inventory_items i
  WHERE i.drug_catalog_id IS NOT NULL
  GROUP BY i.drug_catalog_id
)
SELECT d.id                      AS drug_catalog_id,
       d.internal_code,
       d.brand_name,
       d.unit_of_measure,
       d.packing_specification,
       d.reference_price,
       g.price_type_id,
       g.price                   AS gia_bang_gia,
       CASE WHEN d.reference_price > 0 THEN round(g.price / d.reference_price, 2) END AS ty_le_so_voi_tham_khao,
       l.gia_von_min, l.gia_von_max, l.gia_ban_lo_min, l.gia_ban_lo_max,
       CASE WHEN l.gia_von_max > 0 THEN round(g.price / l.gia_von_max, 2) END          AS ty_le_so_voi_gia_von_max
FROM gia_hieu_luc g
JOIN public.drug_catalogs d ON d.id = g.drug_catalog_id
LEFT JOIN lo_ton l ON l.drug_catalog_id = g.drug_catalog_id
WHERE g.rn = 1
ORDER BY ty_le_so_voi_tham_khao DESC NULLS LAST, d.internal_code;

-- 2) Dong BAT THUONG can Khoa Duoc xem lai tay: gia bang gia lech > 5 lan hoac < 1/5 so voi gia tham khao HOAC gia von lo.
--    (Nguong 5 lan chi la bo loc de rut gon danh sach, KHONG phai quy tac nghiep vu.)
-- SELECT * FROM (<cau truy van o muc 1>) t
-- WHERE t.ty_le_so_voi_tham_khao > 5 OR t.ty_le_so_voi_tham_khao < 0.2
--    OR t.ty_le_so_voi_gia_von_max > 5 OR t.ty_le_so_voi_gia_von_max < 0.2;

-- 3) Thuoc dang ton kho/dang duoc ke nhung KHONG co gia hieu luc (de biet pham vi bi chan khi chan phat thuoc thieu gia — quyet dinh C-1).
SELECT i.drug_catalog_id, d.internal_code, d.brand_name, SUM(i.quantity_on_hand) AS ton
FROM public.inventory_items i
JOIN public.drug_catalogs d ON d.id = i.drug_catalog_id
WHERE i.drug_catalog_id IS NOT NULL
  AND NOT EXISTS (
        SELECT 1 FROM public.drug_price_items p
        WHERE p.drug_catalog_id = i.drug_catalog_id AND p.status >= 0
          AND p.effective_from <= now() AND (p.effective_to IS NULL OR p.effective_to >= now()))
GROUP BY i.drug_catalog_id, d.internal_code, d.brand_name
ORDER BY ton DESC;
