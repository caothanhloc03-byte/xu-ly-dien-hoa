/* AURON trong Echem Studio: tra cứu hướng dẫn của app (không cần mô hình AI).
   Dữ liệu /kien_thuc.json do auron_cua_so.py dựng từ huong_dan_phep_do.py + HUONG_DAN.md.
   Dùng hai việc: (1) trả lời ngay khi chưa bật "bộ não"; (2) đưa đoạn hướng dẫn liên quan vào câu lệnh cho mô hình để nó trả lời đúng app. */
(function (g) {
  'use strict';
  var DU_LIEU = [];
  var DUNG = ['la','cua','cho','va','nhu','the','nao','gi','co','khong','lam','sao','toi','ban','app','trong','duoc','hay','mot','cac','nhung',
              'de','thi','bi','voi','den','tu','o','tai','nay','do','em','minh','xin','vui','long','giup','can','muon','hoi','biet','ve','nhe','a','khi'];

  function chuan(s) {
    s = String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd');
    return s.replace(/[^a-z0-9+]+/g, ' ').trim();
  }
  function tach(s) {
    return chuan(s).split(' ').filter(function (t) { return t.length >= 2 && DUNG.indexOf(t) < 0; });
  }
  function dat(ds) {
    DU_LIEU = (ds || []).map(function (m) {
      var tk = (m.tu_khoa || []).map(chuan);
      return { m: m, tk: tk, tkTok: tach(tk.join(' ')), tenTok: tach(m.ten), tomTok: tach(m.tom_tat), ndTok: tach(m.noi_dung) };
    });
    var n = DU_LIEU.length || 1;
    DU_LIEU.forEach(function (e) {
      e.set = {};
      e.tkTok.concat(e.tenTok, e.tomTok, e.ndTok).forEach(function (t) { e.set[t] = 1; });
    });
    var df = {};
    DU_LIEU.forEach(function (e) { Object.keys(e.set).forEach(function (t) { df[t] = (df[t] || 0) + 1; }); });
    DU_LIEU.idf = function (t) { return Math.log(1 + n / (df[t] || 1)); };
  }
  function diem(q) {
    var qn = ' ' + chuan(q) + ' ', qt = tach(q);
    return DU_LIEU.map(function (e) {
      var s = 0, khop = 0;
      e.tk.forEach(function (p) { if (p.length >= 3 && qn.indexOf(' ' + p + ' ') >= 0) s += 6; });
      qt.forEach(function (t) {
        var w = DU_LIEU.idf(t), h = 0;
        if (e.m.phu) { if (e.tkTok.indexOf(t) >= 0) { h += 8; khop++; } s += h * w; return; }     // nhật ký phiên bản chỉ tìm theo số phiên bản
        if (e.tkTok.indexOf(t) >= 0) h += 4;
        if (e.tenTok.indexOf(t) >= 0) h += 3;
        if (e.tomTok.indexOf(t) >= 0) h += 1.5;
        if (h > 0) khop++;
        if (e.ndTok.indexOf(t) >= 0) h += 0.6;
        s += h * w;
      });
      if (!khop) s = 0;                            // chỉ khớp trong nội dung dài thì không đủ để kết luận
      return { e: e.m, s: s };
    }).sort(function (a, b) { return b.s - a.s; });
  }
  var NGUONG = 5;
  function moiNhat(q) {
    if (!/\b(ban moi|co gi moi|cap nhat|phien ban)\b/.test(chuan(q))) return null;
    var v = DU_LIEU.map(function (e) { var m = /^v(\d+)/i.exec(e.m.ten); return m ? { n: +m[1], m: e.m } : null; }).filter(Boolean);
    v.sort(function (a, b) { return b.n - a.n; });
    return v.length ? v.slice(0, 2).map(function (x) { return x.m; }) : null;
  }
  function tim(q, toiDa) {
    var mn = moiNhat(q);
    if (mn) return mn.slice(0, toiDa || 2);
    var d = diem(q).filter(function (x) { return x.s >= NGUONG; });
    if (d.length) d = d.filter(function (x) { return x.s >= d[0].s * 0.5; });          // mục thứ hai phải đủ gần mục đầu
    return d.slice(0, toiDa || 2).map(function (x) { return x.e; });
  }
  function cat(s, n) { s = String(s || ''); return s.length <= n ? s : s.slice(0, n - 1).replace(/\s+\S*$/, '') + '…'; }
  function lietKe(a, n, moi) {
    return (a || []).slice(0, n).map(function (x, i) { return (moi ? (i + 1) + '. ' : '• ') + cat(x, 220); }).join('\n');
  }
  // Câu trả lời trực tiếp từ hướng dẫn (khi chưa bật bộ não)
  function traLoiNhanh(q) {
    var ds = tim(q, 2);
    if (!ds.length) return null;
    var m = ds[0], c = chuan(q), t = m.ten + '\n' + cat(m.tom_tat, 420);
    if (/\b(cach|buoc|huong dan|lam sao|thao tac|bat dau|dung)\b/.test(c) && m.buoc && m.buoc.length) t += '\n\nCác bước:\n' + lietKe(m.buoc, 6, true);
    else if (/\b(cong thuc|phep tinh|tinh|bang)\b/.test(c) && m.phep_tinh && m.phep_tinh.length) t += '\n\nPhép tính:\n' + lietKe(m.phep_tinh, 5);
    else if (/\b(loi|sai|khong ra|bao loi|van de|that bai)\b/.test(c) && m.loi && m.loi.length) t += '\n\nLỗi thường gặp:\n' + lietKe(m.loi, 5);
    else if (/\b(tieu chi|nguong|tot|chat luong|danh gia)\b/.test(c) && m.tieu_chi && m.tieu_chi.length) t += '\n\nTiêu chí:\n' + lietKe(m.tieu_chi, 5);
    else if (m.buoc && m.buoc.length) t += '\n\nCác bước chính:\n' + lietKe(m.buoc, 4, true);
    if (ds[1]) t += '\n\nXem thêm: ' + ds[1].ten;
    return { ten: m.ten, text: t };
  }
  // Đoạn hướng dẫn đưa vào câu lệnh hệ thống cho mô hình (giới hạn dung lượng vì mô hình nhỏ có ngữ cảnh ngắn)
  function nguCanh(q, toiDa) {
    var ds = tim(q, 2);
    if (!ds.length) return '';
    var gioi = Math.floor((toiDa || 1800) / ds.length);
    return ds.map(function (m) { return '## ' + m.ten + '\n' + cat(m.noi_dung, gioi); }).join('\n\n');
  }
  async function tai(url) {
    var r = await fetch(url || 'kien_thuc.json', { cache: 'no-store' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var j = await r.json();
    dat(j.muc || []);
    return DU_LIEU.length;
  }
  var api = { chuan: chuan, dat: dat, tim: tim, diem: diem, traLoiNhanh: traLoiNhanh, nguCanh: nguCanh, tai: tai, soMuc: function () { return DU_LIEU.length; } };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else g.TroGiup = api;
})(typeof window !== 'undefined' ? window : globalThis);
