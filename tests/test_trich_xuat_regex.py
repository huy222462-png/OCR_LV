from bo_xu_ly.trich_xuat_regex import extract_so_hieu, extract_ngay, extract_trich_yeu

cases = [
    {
        'text': 'Số: 123/QĐ-UBND\nNgày 12/05/2024\nV/v: Về việc ban hành...',
        'so': '123/QĐ-UBND',
        'ngay': '2024-05-12',
        'trich': 'Về việc ban hành...'
    },
    {
        'text': 'Số 45/TTr-NH\nNgày 1 tháng 6 năm 2023\nV: Tờ trình về...',
        'so': '45/TTr-NH',
        'ngay': '2023-06-01',
        'trich': 'Tờ trình về...'
    },
    {
        'text': 'V/v- Phê duyệt kế hoạch\nSố: 78/KT-2022',
        'so': '78/KT-2022',
        'ngay': None,
        'trich': 'Phê duyệt kế hoạch'
    },
]

def run():
    ok = 0
    total = 0
    lines = []
    for c in cases:
        total += 1
        so = extract_so_hieu(c['text'])
        ngay = extract_ngay(c['text'])
        trich = extract_trich_yeu(c['text'])
        lines.append('CASE: ' + c['text'][:200].replace('\n',' '))
        lines.append(f" expected so= {c['so']}  got= {so}")
        lines.append(f" expected ngay= {c['ngay']}  got= {ngay}")
        lines.append(f" expected trich= {c['trich']}  got= {trich}")
        ok += (so == c['so']) + (ngay == c['ngay']) + ( (trich or '').startswith((c['trich'] or '')[:5]) )
        lines.append('---')

    lines.append(f'Score: {ok} / {total*3} (field matches)')
    with open('tests/results_regex.txt','w',encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return 0

if __name__ == '__main__':
    run()
