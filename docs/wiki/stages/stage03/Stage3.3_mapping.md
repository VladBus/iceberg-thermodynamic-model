# Stage 3.3 — Restore 3D Momentum: Mapping Report

Дата: 2026-08-16
Статус: ФАЗА A завершена (исследование + mapping). Код не написан.

## Источник исторического кода

Block 200/210/280 идентичны во всех версиях:

- `Nesterov_last.txt:2110-2260` (block 200/210), `2260-2310` (block 280)
- `Dmitriev.txt:2198-2310`
- `model/Coupl1.f90:880-1060` (самый чистый, используется как эталон)

Порядок в суточном цикле (Coupl1.f90):

```
... W-блок (строки ~500-567) ...
GO TO 888          ! пропускает устаревшую часть
! 888 CONTINUE (876)
block 200: 3D momentum (U' из U1, Coriolis + baroclinic + DPX + Laplacian)
block 210: вертикальная вязкость (Thomas algorithm) -> U2
CALL shal()        ! баротропная мода
block 280: возврат баротропной компоненты (U2 = U2 + SUM, SUM = (-ΣU2·DZZ + 0.5·(UP2+UP2))/HHT)
```

Этот порядок соответствует текущему main.f90:

```
call advs(); call advt()  ! уже есть (строки 480-481)
call conv_adj()           ! уже есть (Stage 3.2)
  --> здесь вставить block 200 + block 210
call shal()               ! уже есть (строка 486)
  --> здесь заменить временный код Stage 1 (u2=up2/hu, v2=vp2/hv)
      на block 280
```

## Таблица mapping: Historical -> Current

| Historical                       | Current                 | Dims         | Units                       | Source                            | Consumer                         |
| -------------------------------- | ----------------------- | ------------ | --------------------------- | --------------------------------- | -------------------------------- |
| UIJ (block 200)                  | u1(i,j,k)               | (is1,js1,ks) | см/с                        | U1 = U2 в начале суток (main:311) | block 200                        |
| VIJ (block 200)                  | v1(i,j,k)               | (is1,js1,ks) | см/с                        | V1 = V2 в начале суток            | block 200                        |
| U2(I,J,K) (block 200 out)        | u2(i,j,k)               | (is1,js1,ks) | см/с                        | block 200                         | block 210, ice stress, advection |
| V2(I,J,K)                        | v2(i,j,k)               | (is1,js1,ks) | см/с                        | block 200                         | block 210, ice, advection        |
| U1 (block 210 in)                | u2(i,j,k)               | (is1,js1,ks) | см/с                        | результат block 200               | block 210 (NU, direct)           |
| UP2(I,J), UP2(I2,J)              | up2(i,j), up2(i-1,j)    | (is1,js1)    | см²/с                       | shallow_water (barotropic)        | block 280                        |
| VP2(I,J), VP2(I,J2)              | vp2(i,j), vp2(i,j-1)    | (is1,js1)    | см²/с                       | shallow_water                     | block 280                        |
| SUM, SUM1                        | локальные               | scalar       | см/с                        | block 280                         | U2/V2 поправка                   |
| SUM, SUM1 (block 200)            | локальные               | scalar       | г/см³·см (баротр. интеграл) | block 200                         | AUU/AVV                          |
| RI, RIJ, RI2J, RIJ2, RI2J2       | ro(i,j,k) и соседи      | (is1,js1,ks) | г/см³ (аномалия)            | conv_adj (Stage 3.2)              | block 200                        |
| DZZ = DZ(1) (block 200)          | dz(1)                   | scalar       | см                          | param data Z                      | block 200                        |
| DZZ1 = DZ(K1)                    | dz(k+1)                 | scalar       | см                          | param                             | block 200                        |
| DZZ = DZ1(K) (block 210/280)     | dz1(k)                  | scalar       | см                          | param                             | block 210/280                    |
| HU (в block 280 не используется) | hu(i,j)                 | (is1,js1)    | см                          | grid_coupling                     | (barotropic)                     |
| HHT = map1(I,J)                  | map1(i,j)               | (is1,js1)    | см                          | grid_coupling:186-220             | block 200/210/280                |
| FKU(I,J)                         | fku(i,j)                | (is1,js1)    | 1/с                         | grid_coupling                     | block 200 (Coriolis)             |
| DPX(I,J)                         | dpx(i,j)                | (is1,js1)    | hPa/см                      | wind_forcing                      | block 200                        |
| DPY(I,J)                         | dpy(i,j)                | (is1,js1)    | hPa/см                      | wind_forcing                      | block 200                        |
| SLAPU                            | локальный               | scalar       | см/с                        | u1 соседи                         | block 200                        |
| SLAPV                            | локальный               | scalar       | см/с                        | v1 соседи                         | block 200                        |
| NU = RR(K) (block 210)           | локальный rr(k)         | ks           | см²/с                       | из U2/V2 shear                    | block 210                        |
| UCA, UNU, VCA, VNU               | uca/unu/vca/vnu (param) | (ks1)        | безразм./см/с               | param.f90:47 (double)             | block 210                        |
| SKZ(I,J) = RR(1)                 | skz(i,j)                | (is1,js1)    | см²/с                       | block 210                         | термодинамика                    |
| TX(I,J), TY(I,J)                 | tx(i,j), ty(i,j)        | (is1,js1)    | дин/см²                     | wind_forcing                      | block 210 (UNU/VNU)              |
| TXIC(I,J), TYIC(I,J)             | txic(i,j), tyic(i,j)    | (is1,js1)    | дин/см²                     | ice stress                        | block 210                        |
| ANS(I,J)                         | ans(i,j)                | (is1,js1)    | безразм. (0..1)             | ice_redis                         | block 210 (взвешивание)          |
| A1 = 0.25·ΣANS                   | локальный               | scalar       | безразм.                    | ans соседи                        | block 210                        |
| YYY = 0.25·ΣYM2                  | локальный               | scalar       | см                          | ym2 соседи                        | block 210 (SL)                   |
| Z(K)                             | z(k)                    | (ks)         | см                          | param data:171-173                | block 200/210                    |
| HHT-Z(K)+50 (bottom layer)       | map1(i,j)-z(k)+50       | scalar       | см                          | param                             | block 210                        |
| KI = KK1(I,J)                    | kk1(i,j)                | (is1,js1)    | —                           | grid_masks                        | block 200/210/280                |
| KI2 = KI-1                       | локальный               | scalar       | —                           | —                                 | block 200/210                    |
| C1 = G/ROC                       | c1 (main:101) = 981     | scalar       | см/с²                       | main                              | block 200                        |
| C3 = AH/(DX·DX)                  | c3 (main:103)           | scalar       | 1/с                         | main                              | block 200                        |
| C8 = 0.25/DX                     | c8 (main:106)           | scalar       | 1/см                        | main                              | block 200                        |
| C9 = 0.5/DX                      | c9 (main:107)           | scalar       | 1/см                        | main (W-блок)                     | block 200? НЕТ — только W        |
| DT                               | dt = 3600               | scalar       | с                           | main                              | block 200/210                    |
| C17                              | c17 (main:113)          | —            | —                           | —                                 | не нужен block 200/210           |

## Ключевые факты из исторического кода

### Block 200 (Coupl1.f90:880-940, Nesterov_last:2110-2160)

- Вход: **U1/V1** (предыдущий бароклинный шаг), RO (после conv_adj), DPX/DPY, FKU.
- Вычисляет баротропно-баротроклинный интеграл плотности (SUM/SUM1) через С-точки RO:
  - `A = RI2J+RIJ-RI2J2-RIJ2` (сверху), `A1` (уровень K), `SUM = Σ(A+A1)·C8·DZZ`
  - `B = RI2J2+RI2J-RIJ2-RIJ`, `SUM1 = Σ(B+B1)·C8·DZZ`
- Лапласиан: `SLAPU = U1(i,j2)+U1(i,j1)+U1(i2,j)+U1(i1,j) - 4·U1(i,j)`
- `AUU = UIJ + ASA1·VIJ + DT·(-C1·SUM - DPX + C3·SLAPU)`
- `AVV = VIJ - ASA1·UIJ + DT·(-C1·SUM1 - DPY + C3·SLAPV)`
- `U2 = (AUU + AVV·ASA1)/ASA`, `V2 = (AVV - AUU·ASA1)/ASA` (ASA1 = FKU·0.5·DT, ASA = 1+ASA1²)
- `IF(HHT.EQ.Z(K))` → U2=V2=0 (уровень совпадает с дном)

### Block 210 (Coupl1.f90:942-1020, Nesterov_last:2165-2250)

- Вход: **U2/V2** (результат block 200), TX/TY, TXIC/TYIC, ANS, YM2, Z, map1.
- Вычисляет коэффициенты вертикальной вязкости NU = L·L·|dU/dz| (L из FF/FF1).
- Решает 3-диагональную систему (прямой ход Томаса) с граничным условием на поверхности
  (wind stress: `(1-A1)·TX + A1·TXIC`) и обратный ход.
- `SKZ(I,J) = RR(1)` — сохраняется для термодинамики.
- Ки-граница: `DZZ = HHT-0.5·(Z(KI)+Z(KI-1))`, `DZZZ = HHT-Z(KI)+50`.
- KI=1: `U2(KI) = UCA(KI)·U2(KI1)+UNU(KI)` (KI1 = KI+1 = 2).

### Block 280 (Coupl1.f90:1031-1058, Nesterov_last:2260-2310)

- Вход: U2/V2 (после block 210), UP2/VP2 (баротропные), map1.
- `SUM = Σ U2·DZZ` по уровням (DZZ = DZ1(K), нижний слой: HHT-0.5·(Z(KI)+Z(KI-1))).
- `SUM = (-SUM + 0.5·(UP2(I,J)+UP2(I2,J)))/HHT`
- `U2(I,J,K) = U2(I,J,K) + SUM` для всех K — вертикальное среднее U' обнуляется.
- Аналогично V.

## Конфликты и решения

1. **GO TO 888** (Nesterov:1797, Coupl1:567, Dmitriev:1876): прыгает к `888 CONTINUE`,
   пропуская старую секцию advS/advT/horiz-diff/vert-diff. В Coupl1 advS/advT/conv_adj
   вызываются ДО 888 (строки 779-846). Решение: порядок в main.f90 сохраняется
   (advs/advt/conv_adj уже стоят до shal), block 200/210 вставляются после conv_adj,
   block 280 заменяет код Stage 1. GO TO 888 не воспроизводится (не нужен).

2. **U1/U2 семантика**: в историческом коде U1 = U2 в начале каждого бароклинного шага
   (arrays redetermination, Coupl1:365-366; main.f90:308-311 уже делает это).
   block 200 читает U1 (предыдущий шаг), block 210 читает U2 (только что вычисленный).
   В текущей модели то же самое: `u1 = u2` (main:311), block 200 использует `u1`,
   block 210 использует `u2`.

3. **map1 vs HT**: block 200/210/280 используют `map1` (усреднённая глубина по 4 T-точкам).
   Текущая модель имеет map1 (grid_coupling:186-220). Используется как HHT.

4. **KI = KK1(I,J)**: в block 200/210/280 используются маски **KK1** (U/V ячейки),
   НЕ KT1 (T/S ячейки). Проверено: текущий main использует kk1 в ледовом блоке
   (main:336) и kt1 для возврата скоростей. block 200/210/280 должны использовать kk1.

5. **DPX/DPY единицы**: исторический комментарий в Nesterov: `DPX,DPY [гПа/км]`.
   В block 200: `DT·(-C1·SUM - DPX + C3·SLAPU)`. DPX входит с тем же весом, что C1·SUM
   (см/с²). Текущая wind_forcing даёт dpx/dpy в hPa/см (см. AGENTS.md: `dpx=(p1(i,j+1)-p1(i,j))·1e3/dxx`).
   ТРЕБУЕТ ПРОВЕРКИ единиц в ФАЗЕ B: исторический DPX может быть в гПа/км, тогда
   `dpx_current [hPa/см] × 1e5 = dpx_hist [hPa/км]`. Это критично.

6. **TX/TY**: ветровое напряжение в дин/см². В текущем коде tx/ty от wind_forcing
   (см. AGENTS.md: `cof=(1.1+0.04·V·1e-2)·V²·1.29e-6`). Единицы совпадают.

7. **RO**: заполняется conv_adj (Stage 3.2). Но в block 200 нужен RO **после** conv_adj
   на текущем шаге — это уже так (conv_adj вызывается перед block 200).

8. **C1 = G/ROC = 981**: в текущем main.f90 c1 = g/roc = 981/1 = 981. Совпадает.

## Что не реализовано (ФАЗА A дефицит)

- В историческом коде block 200 включает ветер как граничное условие только в block 210
  (через TX/TY). block 200 сам не содержит ветра — только Coriolis, baroclinic, DPX, Laplacian.
- Проверить в ФАЗЕ B: используется ли ветер в block 200 в какой-либо версии.

## Вывод ФАЗЫ A

Mapping всех критических переменных ДОКАЗАН:

- DZZ/DZZ1 → dz/dz1 (param) ✓
- HU/HV → используются только barotropic (в block 280 НЕ нужны — там map1/HHT) ✓
- UP2/VP2 → up2/vp2 (param) ✓
- RI → ro(i,j,k) ✓
- DPX/DPY → dpx/dpy (единицы ТРЕБУЮТ проверки в ФАЗЕ B) ⚠
