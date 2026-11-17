"""
Wyckoff Analysis Engine
Wyckoff + SMC Spot Swing Agent

This module identifies a recent 4H trading range, detects simplified Wyckoff
events inside that range, and infers bias/phase from ordered evidence.
Detections are heuristic evidence for later SMC confluence, not certainty.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

try:
    from .market_data import Candle, MarketData, validate_market_data
except ImportError:  # Allows: python src/wyckoff.py
    from market_data import Candle, MarketData, validate_market_data


@dataclass
class TradingRange:
    support: float
    resistance: float
    midpoint: float
    width_pct: float
    start_index: int
    end_index: int
    stability_score: float
    support_touches: int
    resistance_touches: int


@dataclass
class WyckoffEvent:
    code: str
    index: int
    price: float
    confidence: float
    note: str


@dataclass
class WyckoffAnalysis:
    symbol: str
    bias: str
    phase: str
    confidence: float
    trading_range: TradingRange | None
    events: list[WyckoffEvent]
    interpretation: str
    errors: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _spread(candle: Candle) -> float:
    return max(candle.high - candle.low, 0.0)


def _close_location(candle: Candle) -> float:
    spread = _spread(candle)
    return (candle.close - candle.low) / spread if spread else 0.5


def _quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = round((len(ordered) - 1) * fraction)
    return ordered[max(0, min(index, len(ordered) - 1))]


def _volume_baseline(candles: list[Candle], index: int, floor: int, lookback: int = 10) -> float:
    start = max(floor, index - lookback)
    previous = candles[start:index]
    return _mean(c.volume for c in previous) if previous else candles[index].volume


def detect_trading_range(candles: list[Candle], lookback: int = 30) -> TradingRange | None:
    """Detect a recent sideways 4H auction rather than any arbitrary high/low box."""

    if len(candles) < 16:
        return None

    window = candles[-lookback:]
    start_index = len(candles) - len(window)
    lows = [c.low for c in window]
    highs = [c.high for c in window]
    closes = [c.close for c in window]

    support = _quantile(lows, 0.20)
    resistance = _quantile(highs, 0.80)
    if resistance <= support:
        return None

    width = resistance - support
    midpoint = (support + resistance) / 2
    width_pct = (width / midpoint) * 100 if midpoint else 0.0
    if width_pct < 1.0:
        return None

    third = max(3, len(window) // 3)
    displacement_ratio = abs(_mean(closes[-third:]) - _mean(closes[:third])) / width
    if displacement_ratio > 0.65:
        return None

    buffer = width * 0.20
    contained = sum(
        support - buffer <= candle.close <= resistance + buffer
        for candle in window
    )
    containment_ratio = contained / len(window)
    if containment_ratio < 0.72:
        return None

    touch_zone = width * 0.22
    support_touches = sum(c.low <= support + touch_zone for c in window)
    resistance_touches = sum(c.high >= resistance - touch_zone for c in window)
    if support_touches < 2 or resistance_touches < 2:
        return None

    stability = 100.0
    stability -= min(45.0, displacement_ratio * 55.0)
    stability -= max(0.0, 0.90 - containment_ratio) * 100.0
    stability += min(10.0, (support_touches + resistance_touches - 4) * 1.5)
    stability = max(0.0, min(100.0, stability))

    return TradingRange(
        support=round(support, 8),
        resistance=round(resistance, 8),
        midpoint=round(midpoint, 8),
        width_pct=round(width_pct, 2),
        start_index=start_index,
        end_index=len(candles) - 1,
        stability_score=round(stability, 1),
        support_touches=support_touches,
        resistance_touches=resistance_touches,
    )


def _window_indices(trading_range: TradingRange) -> range:
    return range(trading_range.start_index, trading_range.end_index + 1)


def _detect_climaxes(candles: list[Candle], trading_range: TradingRange) -> list[WyckoffEvent]:
    events: list[WyckoffEvent] = []
    window = candles[trading_range.start_index : trading_range.end_index + 1]
    avg_spread = _mean(_spread(c) for c in window) or 1.0

    for index in _window_indices(trading_range):
        candle = candles[index]
        baseline = _volume_baseline(candles, index, trading_range.start_index)
        volume_ratio = candle.volume / baseline if baseline else 1.0
        spread_ratio = _spread(candle) / avg_spread if avg_spread else 1.0
        close_location = _close_location(candle)

        near_support = candle.low <= trading_range.support * 1.015
        near_resistance = candle.high >= trading_range.resistance * 0.985

        if near_support and volume_ratio >= 1.45 and spread_ratio >= 0.65 and close_location >= 0.35:
            confidence = min(95.0, 58 + (volume_ratio - 1.45) * 20 + max(0.0, close_location - 0.35) * 30)
            events.append(WyckoffEvent("SC", index, candle.low, round(confidence, 1), "High-volume downside climax with rejection near support."))

        if near_resistance and volume_ratio >= 1.45 and spread_ratio >= 0.65 and close_location <= 0.65:
            confidence = min(95.0, 58 + (volume_ratio - 1.45) * 20 + max(0.0, 0.65 - close_location) * 30)
            events.append(WyckoffEvent("BC", index, candle.high, round(confidence, 1), "High-volume upside climax with rejection near resistance."))

    return events


def _first_after(events: list[WyckoffEvent], code: str, after_index: int = -1) -> WyckoffEvent | None:
    candidates = [event for event in events if event.code == code and event.index > after_index]
    return min(candidates, key=lambda event: event.index) if candidates else None


def _detect_automatic_reactions(
    candles: list[Candle], trading_range: TradingRange, events: list[WyckoffEvent]
) -> list[WyckoffEvent]:
    detected: list[WyckoffEvent] = []
    width = trading_range.resistance - trading_range.support

    for climax in [event for event in events if event.code == "SC"]:
        stop = min(trading_range.end_index, climax.index + 8)
        candidates = [(i, candles[i]) for i in range(climax.index + 1, stop + 1)]
        if not candidates:
            continue
        index, candle = max(candidates, key=lambda item: item[1].high)
        if candle.high >= trading_range.midpoint + width * 0.10:
            detected.append(WyckoffEvent("AR", index, candle.high, 68.0, "Automatic rally following a selling climax."))

    for climax in [event for event in events if event.code == "BC"]:
        stop = min(trading_range.end_index, climax.index + 8)
        candidates = [(i, candles[i]) for i in range(climax.index + 1, stop + 1)]
        if not candidates:
            continue
        index, candle = min(candidates, key=lambda item: item[1].low)
        if candle.low <= trading_range.midpoint - width * 0.10:
            detected.append(WyckoffEvent("AR_DOWN", index, candle.low, 68.0, "Automatic reaction following a buying climax."))

    return detected


def _detect_secondary_tests(
    candles: list[Candle], trading_range: TradingRange, events: list[WyckoffEvent]
) -> list[WyckoffEvent]:
    detected: list[WyckoffEvent] = []
    width = trading_range.resistance - trading_range.support
    lower_zone = trading_range.support + width * 0.20
    upper_zone = trading_range.resistance - width * 0.20

    for sc in [event for event in events if event.code == "SC"]:
        ar = _first_after(events, "AR", sc.index)
        if ar is None:
            continue
        for index in range(ar.index + 1, trading_range.end_index + 1):
            candle = candles[index]
            baseline = _volume_baseline(candles, index, trading_range.start_index)
            volume_ratio = candle.volume / baseline if baseline else 1.0
            if candle.low <= lower_zone and candle.low >= sc.price * 0.985 and _close_location(candle) >= 0.35 and volume_ratio <= 1.15:
                detected.append(WyckoffEvent("ST", index, candle.low, 68.0, "Controlled lower-range retest after SC and AR."))
                break

    for bc in [event for event in events if event.code == "BC"]:
        ar_down = _first_after(events, "AR_DOWN", bc.index)
        if ar_down is None:
            continue
        for index in range(ar_down.index + 1, trading_range.end_index + 1):
            candle = candles[index]
            baseline = _volume_baseline(candles, index, trading_range.start_index)
            volume_ratio = candle.volume / baseline if baseline else 1.0
            if candle.high >= upper_zone and candle.high <= bc.price * 1.015 and _close_location(candle) <= 0.65 and volume_ratio <= 1.15:
                detected.append(WyckoffEvent("UT_TEST", index, candle.high, 65.0, "Controlled upper-range retest after BC and automatic reaction."))
                break

    return detected


def _detect_springs_upthrusts(
    candles: list[Candle], trading_range: TradingRange, events: list[WyckoffEvent]
) -> list[WyckoffEvent]:
    detected: list[WyckoffEvent] = []
    width = trading_range.resistance - trading_range.support
    spring_threshold = trading_range.support - width * 0.06
    upthrust_threshold = trading_range.resistance + width * 0.06

    st = _first_after(events, "ST")
    if st is not None:
        for index in range(st.index + 1, trading_range.end_index + 1):
            candle = candles[index]
            if candle.low < spring_threshold and candle.close > trading_range.support and _close_location(candle) >= 0.45:
                reclaim = (candle.close - trading_range.support) / width
                detected.append(WyckoffEvent("SPRING", index, candle.low, min(95.0, round(72 + reclaim * 45, 1)), "Sweep below support followed by a meaningful reclaim."))
                break

    upper_test = _first_after(events, "UT_TEST")
    if upper_test is not None:
        for index in range(upper_test.index + 1, trading_range.end_index + 1):
            candle = candles[index]
            if candle.high > upthrust_threshold and candle.close < trading_range.resistance and _close_location(candle) <= 0.55:
                rejection = (trading_range.resistance - candle.close) / width
                detected.append(WyckoffEvent("UTAD", index, candle.high, min(95.0, round(72 + rejection * 45, 1)), "Sweep above resistance followed by rejection into range."))
                break

    return detected


def _detect_post_sweep_tests(
    candles: list[Candle], trading_range: TradingRange, events: list[WyckoffEvent]
) -> list[WyckoffEvent]:
    detected: list[WyckoffEvent] = []
    width = trading_range.resistance - trading_range.support

    spring = _first_after(events, "SPRING")
    if spring is not None:
        for index in range(spring.index + 1, min(trading_range.end_index, spring.index + 5) + 1):
            candle = candles[index]
            baseline = _volume_baseline(candles, index, trading_range.start_index)
            volume_ratio = candle.volume / baseline if baseline else 1.0
            if candle.low > spring.price and candle.low <= trading_range.support + width * 0.28 and candle.close > trading_range.support and volume_ratio <= 1.20:
                detected.append(WyckoffEvent("TEST", index, candle.low, 70.0, "Post-spring test holds above the spring low on controlled volume."))
                break

    utad = _first_after(events, "UTAD")
    if utad is not None:
        for index in range(utad.index + 1, min(trading_range.end_index, utad.index + 5) + 1):
            candle = candles[index]
            baseline = _volume_baseline(candles, index, trading_range.start_index)
            volume_ratio = candle.volume / baseline if baseline else 1.0
            if candle.high < utad.price and candle.high >= trading_range.resistance - width * 0.28 and candle.close < trading_range.resistance and volume_ratio <= 1.20:
                detected.append(WyckoffEvent("UTAD_TEST", index, candle.high, 70.0, "Post-UTAD test fails below the upthrust high on controlled volume."))
                break

    return detected


def _detect_sos_sow(
    candles: list[Candle], trading_range: TradingRange, events: list[WyckoffEvent]
) -> list[WyckoffEvent]:
    detected: list[WyckoffEvent] = []
    recent_start = max(trading_range.start_index, trading_range.end_index - 9)
    baseline_slice = candles[max(trading_range.start_index, recent_start - 12):recent_start]
    fallback_slice = candles[recent_start : trading_range.end_index + 1]
    baseline_volume = _mean(c.volume for c in baseline_slice) or _mean(c.volume for c in fallback_slice)

    spring = _first_after(events, "SPRING")
    utad = _first_after(events, "UTAD")

    for index in range(recent_start, trading_range.end_index + 1):
        candle = candles[index]
        volume_ratio = candle.volume / baseline_volume if baseline_volume else 1.0

        if spring is not None and index > spring.index and candle.close > trading_range.resistance and candle.close > candle.open and volume_ratio >= 1.10:
            detected.append(WyckoffEvent("SOS", index, candle.close, min(95.0, round(72 + (volume_ratio - 1.1) * 25, 1)), "Bullish expansion above resistance after spring evidence."))
            break

        if utad is not None and index > utad.index and candle.close < trading_range.support and candle.close < candle.open and volume_ratio >= 1.10:
            detected.append(WyckoffEvent("SOW", index, candle.close, min(95.0, round(72 + (volume_ratio - 1.1) * 25, 1)), "Bearish expansion below support after upthrust evidence."))
            break

    return detected


def _detect_lps_lpsy(
    candles: list[Candle], trading_range: TradingRange, events: list[WyckoffEvent]
) -> list[WyckoffEvent]:
    detected: list[WyckoffEvent] = []
    width = trading_range.resistance - trading_range.support

    sos = _first_after(events, "SOS")
    if sos is not None:
        sos_volume = candles[sos.index].volume
        for index in range(sos.index + 1, min(trading_range.end_index, sos.index + 6) + 1):
            candle = candles[index]
            if candle.low <= trading_range.resistance + width * 0.25 and candle.close >= trading_range.resistance and candle.volume <= sos_volume * 0.90:
                detected.append(WyckoffEvent("LPS", index, candle.low, 72.0, "Last-point-of-support style retest after SOS."))
                break

    sow = _first_after(events, "SOW")
    if sow is not None:
        sow_volume = candles[sow.index].volume
        for index in range(sow.index + 1, min(trading_range.end_index, sow.index + 6) + 1):
            candle = candles[index]
            if candle.high >= trading_range.support - width * 0.25 and candle.close <= trading_range.support and candle.volume <= sow_volume * 0.90:
                detected.append(WyckoffEvent("LPSY", index, candle.high, 72.0, "Last-point-of-supply style retest after SOW."))
                break

    return detected


def _dedupe_events(events: list[WyckoffEvent]) -> list[WyckoffEvent]:
    best: dict[tuple[str, int], WyckoffEvent] = {}
    for event in events:
        key = (event.code, event.index)
        existing = best.get(key)
        if existing is None or event.confidence > existing.confidence:
            best[key] = event
    return sorted(best.values(), key=lambda event: (event.index, event.code))


def _infer_bias_phase(
    events: list[WyckoffEvent], candles: list[Candle], trading_range: TradingRange
) -> tuple[str, str, float, str]:
    bullish = 0
    bearish = 0

    sc = _first_after(events, "SC")
    ar = _first_after(events, "AR", sc.index if sc else -1)
    st = _first_after(events, "ST", ar.index if ar else -1)
    spring = _first_after(events, "SPRING", st.index if st else -1)
    test = _first_after(events, "TEST", spring.index if spring else -1)
    sos = _first_after(events, "SOS", spring.index if spring else -1)
    lps = _first_after(events, "LPS", sos.index if sos else -1)

    if sc and ar:
        bullish += 1
    if sc and ar and st:
        bullish += 2
    if spring:
        bullish += 3
    if test:
        bullish += 1
    if sos:
        bullish += 3
    if lps:
        bullish += 2

    bc = _first_after(events, "BC")
    ar_down = _first_after(events, "AR_DOWN", bc.index if bc else -1)
    upper_test = _first_after(events, "UT_TEST", ar_down.index if ar_down else -1)
    utad = _first_after(events, "UTAD", upper_test.index if upper_test else -1)
    utad_test = _first_after(events, "UTAD_TEST", utad.index if utad else -1)
    sow = _first_after(events, "SOW", utad.index if utad else -1)
    lpsy = _first_after(events, "LPSY", sow.index if sow else -1)

    if bc and ar_down:
        bearish += 1
    if bc and ar_down and upper_test:
        bearish += 2
    if utad:
        bearish += 3
    if utad_test:
        bearish += 1
    if sow:
        bearish += 3
    if lpsy:
        bearish += 2

    if bullish >= bearish + 2:
        bias = "ACCUMULATION"
        if lps or sos:
            phase = "D_TO_E"
            interpretation = "Potential accumulation with ordered spring-to-strength evidence."
        elif spring:
            phase = "C_TO_D"
            interpretation = "Potential accumulation after an ordered SC/AR/ST and spring sequence."
        else:
            phase = "B_TO_C"
            interpretation = "Potential accumulation range with early ordered SC/AR/ST evidence."
    elif bearish >= bullish + 2:
        bias = "DISTRIBUTION"
        if lpsy or sow:
            phase = "D_TO_E"
            interpretation = "Potential distribution with ordered upthrust-to-weakness evidence."
        elif utad:
            phase = "C_TO_D"
            interpretation = "Potential distribution after an ordered BC/reaction/test and UTAD sequence."
        else:
            phase = "B_TO_C"
            interpretation = "Potential distribution range with early ordered BC/reaction/test evidence."
    else:
        bias = "NEUTRAL"
        phase = "UNCONFIRMED"
        interpretation = "Trading range detected, but ordered Wyckoff evidence is mixed or insufficient."

    edge = abs(bullish - bearish)
    relevant = [event.confidence for event in events[-6:]]
    event_confidence = _mean(relevant) if relevant else 35.0
    confidence = 30.0 + edge * 7.0 + max(0.0, event_confidence - 50.0) * 0.30
    confidence += max(0.0, trading_range.stability_score - 60.0) * 0.10
    confidence = min(95.0, confidence)
    if bias == "NEUTRAL":
        confidence = min(confidence, 55.0)

    return bias, phase, round(confidence, 1), interpretation


def analyze_wyckoff(market: MarketData, lookback: int = 30) -> W…19985 tokens truncated…],[1792785600000,"100","102","98","100.0","1000",1792799999999],[1792800000000,"100","102","98","100.1","1000",1792814399999],[1792814400000,"100","102","98","100.2","1000",1792828799999],[1792828800000,"100","102","98","100.3","1000",1792843199999],[1792843200000,"100","102","98","100.4","1000",1792857599999],[1792857600000,"100","102","98","100.0","1000",1792871999999],[1792872000000,"100","102","98","100.1","1000",1792886399999],[1792886400000,"100","102","98","100.2","1000",1792900799999],[1792900800000,"100","102","98","100.3","1000",1792915199999],[1792915200000,"100","102","98","100.4","1000",1792929599999],[1792929600000,"100","102","98","100.0","1000",1792943999999],[1792944000000,"100","102","98","100.1","1000",1792958399999],[1792958400000,"100","102","98","100.2","1000",1792972799999],[1792972800000,"100","102","98","100.3","1000",1792987199999],[1792987200000,"100","102","98","100.4","1000",1793001599999],[1793001600000,"100","102","98","100.0","1000",1793015999999],[1793016000000,"100","102","98","100.1","1000",1793030399999],[1793030400000,"100","102","98","100.2","1000",1793044799999],[1793044800000,"100","102","98","100.3","1000",1793059199999],[1793059200000,"100","102","98","100.4","1000",1793073599999],[1793073600000,"100","102","98","100.0","1000",1793087999999],[1793088000000,"100","102","98","100.1","1000",1793102399999],[1793102400000,"100","102","98","100.2","1000",1793116799999],[1793116800000,"100","102","98","100.3","1000",1793131199999],[1793131200000,"100","102","98","100.4","1000",1793145599999],[1793145600000,"100","102","98","100.0","1000",1793159999999],[1793160000000,"100","102","98","100.1","1000",1793174399999],[1793174400000,"100","102","98","100.2","1000",1793188799999],[1793188800000,"100","102","98","100.3","1000",1793203199999],[1793203200000,"100","102","98","100.4","1000",1793217599999],[1793217600000,"100","102","98","100.0","1000",1793231999999],[1793232000000,"100","102","98","100.1","1000",1793246399999],[1793246400000,"100","102","98","100.2","1000",1793260799999],[1793260800000,"100","102","98","100.3","1000",1793275199999],[1793275200000,"100","102","98","100.4","1000",1793289599999],[1793289600000,"100","102","98","100.0","1000",1793303999999],[1793304000000,"100","102","98","100.1","1000",1793318399999],[1793318400000,"100","102","98","100.2","1000",1793332799999],[1793332800000,"100","102","98","100.3","1000",1793347199999],[1793347200000,"100","102","98","100.4","1000",1793361599999],[1793361600000,"100","102","98","100.0","1000",1793375999999],[1793376000000,"100","102","98","100.1","1000",1793390399999],[1793390400000,"100","102","98","100.2","1000",1793404799999],[1793404800000,"100","102","98","100.3","1000",1793419199999],[1793419200000,"100","102","98","100.4","1000",1793433599999],[1793433600000,"100","102","98","100.0","1000",1793447999999],[1793448000000,"100","102","98","100.1","1000",1793462399999],[1793462400000,"100","102","98","100.2","1000",1793476799999],[1793476800000,"100","102","98","100.3","1000",1793491199999],[1793491200000,"100","102","98","100.4","1000",1793505599999],[1793505600000,"100","102","98","100.0","1000",1793519999999],[1793520000000,"100","102","98","100.1","1000",1793534399999],[1793534400000,"100","102","98","100.2","1000",1793548799999],[1793548800000,"100","102","98","100.3","1000",1793563199999],[1793563200000,"100","102","98","100.4","1000",1793577599999],[1793577600000,"100","102","98","100.0","1000",1793591999999],[1793592000000,"100","102","98","100.1","1000",1793606399999],[1793606400000,"100","102","98","100.2","1000",1793620799999],[1793620800000,"100","102","98","100.3","1000",1793635199999],[1793635200000,"100","102","98","100.4","1000",1793649599999],[1793649600000,"100","102","98","100.0","1000",1793663999999],[1793664000000,"100","102","98","100.1","1000",1793678399999],[1793678400000,"100","102","98","100.2","1000",1793692799999],[1793692800000,"100","102","98","100.3","1000",1793707199999],[1793707200000,"100","102","98","100.4","1000",1793721599999],[1793721600000,"100","102","98","100.0","1000",1793735999999],[1793736000000,"100","102","98","100.1","1000",1793750399999],[1793750400000,"100","102","98","100.2","1000",1793764799999],[1793764800000,"100","102","98","100.3","1000",1793779199999],[1793779200000,"100","102","98","100.4","1000",1793793599999],[1793793600000,"100","102","98","100.0","1000",1793807999999],[1793808000000,"100","102","98","100.1","1000",1793822399999],[1793822400000,"100","102","98","100.2","1000",1793836799999],[1793836800000,"100","102","98","100.3","1000",1793851199999],[1793851200000,"100","102","98","100.4","1000",1793865599999],[1793865600000,"100","102","98","100.0","1000",1793879999999],[1793880000000,"100","102","98","100.1","1000",1793894399999],[1793894400000,"100","102","98","100.2","1000",1793908799999],[1793908800000,"100","102","98","100.3","1000",1793923199999],[1793923200000,"100","102","98","100.4","1000",1793937599999],[1793937600000,"100","102","98","100.0","1000",1793951999999],[1793952000000,"100","102","98","100.1","1000",1793966399999],[1793966400000,"100","102","98","100.2","1000",1793980799999],[1793980800000,"100","102","98","100.3","1000",1793995199999],[1793995200000,"100","102","98","100.4","1000",1794009599999],[1794009600000,"100","102","98","100.0","1000",1794023999999],[1794024000000,"100","102","98","100.1","1000",1794038399999],[1794038400000,"100","102","98","100.2","1000",1794052799999],[1794052800000,"100","102","98","100.3","1000",1794067199999],[1794067200000,"100","102","98","100.4","1000",1794081599999],[1794081600000,"100","102","98","100.0","1000",1794095999999],[1794096000000,"100","102","98","100.1","1000",1794110399999],[1794110400000,"100","102","98","100.2","1000",1794124799999],[1794124800000,"100","102","98","100.3","1000",1794139199999],[1794139200000,"100","102","98","100.4","1000",1794153599999],[1794153600000,"100","102","98","100.0","1000",1794167999999],[1794168000000,"100","102","98","100.1","1000",1794182399999],[1794182400000,"100","102","98","100.2","1000",1794196799999],[1794196800000,"100","102","98","100.3","1000",1794211199999],[1794211200000,"100","102","98","100.4","1000",1794225599999],[1794225600000,"100","102","98","100.0","1000",1794239999999],[1794240000000,"100","102","98","100.1","1000",1794254399999],[1794254400000,"100","102","98","100.2","1000",1794268799999],[1794268800000,"100","102","98","100.3","1000",1794283199999],[1794283200000,"100","102","98","100.4","1000",1794297599999],[1794297600000,"100","102","98","100.0","1000",1794311999999],[1794312000000,"100","102","98","100.1","1000",1794326399999],[1794326400000,"100","102","98","100.2","1000",1794340799999],[1794340800000,"100","102","98","100.3","1000",1794355199999],[1794355200000,"100","102","98","100.4","1000",1794369599999],[1794369600000,"100","102","98","100.0","1000",1794383999999],[1794384000000,"100","102","98","100.1","1000",1794398399999],[1794398400000,"100","102","98","100.2","1000",1794412799999],[1794412800000,"100","102","98","100.3","1000",1794427199999],[1794427200000,"100","102","98","100.4","1000",1794441599999],[1794441600000,"100","102","98","100.0","1000",1794455999999],[1794456000000,"100","102","98","100.1","1000",1794470399999],[1794470400000,"100","102","98","100.2","1000",1794484799999],[1794484800000,"100","102","98","100.3","1000",1794499199999],[1794499200000,"100","102","98","100.4","1000",1794513599999],[1794513600000,"100","102","98","100.0","1000",1794527999999],[1794528000000,"100","102","98","100.1","1000",1794542399999],[1794542400000,"100","102","98","100.2","1000",1794556799999],[1794556800000,"100","102","98","100.3","1000",1794571199999],[1794571200000,"100","102","98","100.4","1000",1794585599999],[1794585600000,"100","102","98","100.0","1000",1794599999999],[1794600000000,"100","102","98","100.1","1000",1794614399999],[1794614400000,"100","102","98","100.2","1000",1794628799999],[1794628800000,"100","102","98","100.3","1000",1794643199999],[1794643200000,"100","102","98","100.4","1000",1794657599999],[1794657600000,"100","102","98","100.0","1000",1794671999999],[1794672000000,"100","102","98","100.1","1000",1794686399999],[1794686400000,"100","102","98","100.2","1000",1794700799999],[1794700800000,"100","102","98","100.3","1000",1794715199999],[1794715200000,"100","102","98","100.4","1000",1794729599999],[1794729600000,"100","102","98","100.0","1000",1794743999999],[1794744000000,"100","102","98","100.1","1000",1794758399999],[1794758400000,"100","102","98","100.2","1000",1794772799999],[1794772800000,"100","102","98","100.3","1000",1794787199999],[1794787200000,"100","102","98","100.4","1000",1794801599999],[1794801600000,"100","102","98","100.0","1000",1794815999999],[1794816000000,"100","102","98","100.1","1000",1794830399999],[1794830400000,"100","102","98","100.2","1000",1794844799999],[1794844800000,"100","102","98","100.3","1000",1794859199999],[1794859200000,"100","102","98","100.4","1000",1794873599999]]},"cutoff_ms":1794873600000,"kind":"SYNTHETIC_TEST","market":"SPOT","schema":"decision-check.snapshot.v1","source":"https://data-api.binance.vision/api/v3/klines","symbol":"BTCUSDT","venue":"BINANCE"},"snapshot_sha256":"e56de580a6eaa2984152faa7dfb7805733b4f2f573c607bc72fa5d027110b17a","tapeout":{"circuit_id":null,"status":"NOT_REQUESTED"},"upstream_revision":"ca6dce03685317e980d435d22539cc8d0bf45e15"}
