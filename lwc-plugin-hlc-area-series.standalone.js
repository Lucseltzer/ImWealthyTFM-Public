import { customSeriesDefaultOptions as e } from "lightweight-charts";
//#region ../lwc-toolkit/dist/custom-series/visible-bars.js
function t(e, t) {
	return e === null ? {
		from: 0,
		to: 0
	} : {
		from: Math.max(0, e.from),
		to: Math.min(t, e.to)
	};
}
function n(e, t, n = 1) {
	return {
		from: Math.max(0, e.from - n),
		to: Math.min(t, e.to + n)
	};
}
function r(e, n, r) {
	let { from: i, to: a } = t(n, e.length);
	if (i >= a) return [];
	let o = [], s = i;
	for (let t = i + 1; t < a; t++) (e[t].time - e[t - 1].time <= 0 || r?.(e[t - 1], e[t])) && (o.push({
		from: s,
		to: t
	}), s = t);
	return o.push({
		from: s,
		to: a
	}), o;
}
function i(e, t, n) {
	let r = null, i = [];
	return (a, o, s = 1) => {
		let c = e();
		if (c.revision !== r && (r = c.revision, i = c.points.filter(n).map((e) => e.time)), i.length === 0) return !1;
		let l = (e) => {
			let n = 0, r = i.length;
			for (; n < r;) {
				let a = Math.floor((n + r) / 2);
				e(t(i[a])) ? n = a + 1 : r = a;
			}
			return n;
		}, u = l((e) => e === null || e <= a.time);
		if (u >= i.length) return !1;
		let d = l((e) => e === null || e < o.time), f = Math.max(1, s);
		if (d - u < f) return !1;
		let p = 0, m = null;
		for (let e = u; e < d; e++) {
			let n = t(i[e]);
			if (p = n === null ? 0 : m !== null && n === m + 1 ? p + 1 : 1, m = n, p >= f) return !0;
		}
		return !1;
	};
}
function a(e, t, n) {
	return t.x + (e.time - t.time) * n;
}
function o(e) {
	return Math.max(1, e.conflationFactor ?? 1);
}
//#endregion
//#region ../lwc-toolkit/dist/custom-series/options-aware-series.js
function s(e, t, n, r, i, a = 0) {
	let o = [], s = {
		points: [],
		revision: 0
	}, c = () => s, l = (e) => {
		let t = 0, n = o.length;
		for (; t < n;) {
			let r = t + n >> 1;
			o[r] < e ? t = r + 1 : n = r;
		}
		return t;
	}, u, d = t(() => u?.options() ?? n, c);
	u = e.addCustomSeries(d, r, a);
	let f = u, p = (t) => e.horzBehaviour().key(t.time), m = [], h = !1, g = f.setData.bind(f), _ = f.update.bind(f), v = f.applyOptions.bind(f), y = () => {
		!h || m.length !== 0 || (h = !1, s.points.length > 0 && g(s.points.slice()));
	};
	f.subscribeDataChanged(() => {
		let e = m[m.length - 1], t = e?.commit;
		t && (e.commit = null, t(), s.revision++);
	});
	let b = (e, t) => {
		m.push({ commit: e });
		try {
			return t();
		} finally {
			m.pop(), y();
		}
	};
	f.setData = (e) => {
		let t = e.map((e) => ({
			time: p(e),
			point: { ...e }
		})).sort((e, t) => e.time - t.time);
		b(() => {
			o = t.map((e) => e.time), s.points = t.map((e) => e.point);
		}, () => g(e));
	}, f.update = (e, t) => {
		let n = p(e), r = { ...e };
		b(() => {
			let e = l(n);
			o[e] === n ? s.points[e] = r : (o.splice(e, 0, n), s.points.splice(e, 0, r));
		}, () => _(e, t));
	};
	let x = f, S = x.pop?.bind(f);
	return S !== void 0 && (x.pop = (e) => {
		let t = e <= 0 ? [] : f.data().slice(-e).map(p);
		return b(() => {
			for (let e of t) {
				let t = l(e);
				o[t] === e && (o.splice(t, 1), s.points.splice(t, 1));
			}
		}, () => S(e));
	}), f.applyOptions = (e) => {
		let t = i.map((e) => f.options()[e]);
		v(e), i.some((e, n) => f.options()[e] !== t[n]) && (h = !0, y());
	}, f;
}
function c(e, t, n, r, a = [], o = 0) {
	return s(e, (n, r) => {
		let a;
		return a = t(i(r, (t) => e.timeScale().timeToIndex(t, !1), (e) => a.isWhitespace(e)), n), a;
	}, n, r, a, o);
}
//#endregion
//#region src/options.ts
var l = {
	...e,
	highLineColor: "#049981",
	lowLineColor: "#F23645",
	closeLineColor: "#878993",
	highAreaColor: "rgba(4, 153, 129, 0.2)",
	lowAreaColor: "rgba(242, 54, 69, 0.2)",
	highLineWidth: 2,
	lowLineWidth: 2,
	closeLineWidth: 2,
	highLineStyle: 0,
	lowLineStyle: 0,
	closeLineStyle: 0,
	highLineVisible: !0,
	lowLineVisible: !0,
	closeLineVisible: !0,
	areaVisible: !0,
	lineType: "simple",
	highAreaTopColor: "",
	highAreaBottomColor: "",
	lowAreaTopColor: "",
	lowAreaBottomColor: "",
	hoverPointRadius: 4
};
//#endregion
//#region ../lwc-toolkit/dist/custom-series/line-paths.js
function u(e, t, n, r, i, a = !1) {
	let { horizontalPixelRatio: o, verticalPixelRatio: s } = i, c = new Path2D(), l = {
		x: 0,
		y: 0
	}, u = {
		x: 0,
		y: 0
	};
	if (t >= n) return {
		path: c,
		first: l,
		last: u
	};
	let d = a ? n - 1 : t, f = a ? t - 1 : n, p = a ? -1 : 1;
	for (let t = d; t !== f; t += p) {
		let n = e[t], i = n.x * o, a = r(n, t) * s;
		t === d ? (c.moveTo(i, a), l.x = i, l.y = a) : c.lineTo(i, a), u.x = i, u.y = a;
	}
	return {
		path: c,
		first: l,
		last: u
	};
}
function d(e, t, n, r, i, a = !1) {
	let { horizontalPixelRatio: o, verticalPixelRatio: s } = i, c = new Path2D(), l = {
		x: 0,
		y: 0
	}, u = {
		x: 0,
		y: 0
	};
	if (t >= n) return {
		path: c,
		first: l,
		last: u
	};
	let d = a ? n - 1 : t, f = a ? t - 1 : n, p = a ? -1 : 1, m = 0, h = 0;
	for (let t = d; t !== f; t += p) {
		let n = e[t], i = n.x * o, f = r(n, t) * s;
		t === d ? (c.moveTo(i, f), l.x = i, l.y = f) : (c.lineTo(a ? m : i, a ? f : h), c.lineTo(i, f)), m = i, h = f, u.x = i, u.y = f;
	}
	return {
		path: c,
		first: l,
		last: u
	};
}
function f(e, t) {
	let n = new Path2D(e.path);
	return n.lineTo(t.first.x, t.first.y), n.addPath(t.path), n.lineTo(e.first.x, e.first.y), n.closePath(), n;
}
//#endregion
//#region ../lwc-toolkit/dist/custom-series/renderer-base.js
var p = class {
	constructor() {
		Object.defineProperty(this, "data", {
			enumerable: !0,
			configurable: !0,
			writable: !0,
			value: null
		}), Object.defineProperty(this, "options", {
			enumerable: !0,
			configurable: !0,
			writable: !0,
			value: null
		});
	}
	update(e, t) {
		this.data = e, this.options = t;
	}
	draw(e, t, n, r) {
		let i = this.data, a = this.options;
		if (i === null || a === null || i.bars.length === 0) return;
		let o = i.visibleRange;
		if (o === null) return;
		let { from: s, to: c } = o;
		s >= c || e.useBitmapCoordinateSpace((e) => this.drawImpl(e, {
			data: i,
			options: a,
			priceToCoordinate: t,
			from: s,
			to: c,
			isHovered: n ?? !1,
			hitTestData: r
		}));
	}
}, m = {
	Solid: 0,
	Dotted: 1,
	Dashed: 2,
	LargeDashed: 3,
	SparseDotted: 4
};
function h(e, t) {
	switch (e) {
		case m.Solid: return [];
		case m.Dotted: return [t, t];
		case m.Dashed: return [2 * t, 2 * t];
		case m.LargeDashed: return [6 * t, 6 * t];
		case m.SparseDotted: return [t, 4 * t];
		default: return [];
	}
}
function g(e, t, n = 1) {
	let r = h(t, e.lineWidth * n);
	return e.setLineDash(r), r;
}
//#endregion
//#region src/renderer.ts
var _ = 8;
function v(e, t, n) {
	return e < t ? t - e : e > n ? e - n : 0;
}
function y(e) {
	let t = e.hitTestTolerance;
	return typeof t == "number" ? t : _;
}
var b = class extends p {
	_isGap;
	constructor(e) {
		super(), this._isGap = e;
	}
	hitTest(e, t, n) {
		let r = this.data, i = this.options;
		if (r === null || i === null || r.visibleRange === null) return null;
		let a = y(i), o = null, { from: s, to: c } = r.visibleRange;
		for (let i = s; i < c; i++) {
			let s = r.bars[i], c = Math.abs(e - s.x);
			if (c > a) continue;
			let l = n(s.originalData.high), u = n(s.originalData.low);
			if (l === null || u === null) continue;
			let d = v(t, Math.min(l, u), Math.max(l, u)), f = Math.sqrt(c * c + d * d);
			f > a || (o === null || f < o.distance) && (o = {
				distance: f,
				objectId: `hlc-${s.time}`,
				type: "range",
				hitTestData: i
			});
		}
		return o;
	}
	drawImpl(e, t) {
		let { data: i, options: s, priceToCoordinate: c, from: l, to: u, isHovered: d, hitTestData: f } = t, p = n({
			from: l,
			to: u
		}, i.bars.length), m = [];
		for (let e = p.from; e < p.to; e++) {
			let t = i.bars[e], n = t.originalData, r = c(n.high), o = c(n.low), s = c(n.close);
			r !== null && o !== null && s !== null && m.push({
				x: a(t, i.bars[l], i.barSpacing),
				high: r,
				low: o,
				close: s,
				index: e,
				time: t.time
			});
		}
		let h = e.context;
		h.save(), h.lineJoin = "round";
		let g = o(i);
		for (let t of r(m, {
			from: 0,
			to: m.length
		}, (e, t) => t.index !== e.index + 1 || (this._isGap?.(i.bars[e.index], i.bars[t.index], g) ?? !1))) this._drawSegment(e, s, m, t.from, t.to);
		d && typeof f == "number" && this._drawHoverPoints(e, s, m, f), h.restore();
	}
	_drawSegment(e, t, n, r, i) {
		if (r >= i) return;
		let a = t.lineType === "step" ? d : u, o = a(n, r, i, (e) => e.high, e), s = a(n, r, i, (e) => e.low, e), c = a(n, r, i, (e) => e.close, e, !0), l = e.context;
		t.areaVisible && (l.fillStyle = this._areaStyle(e, t.areaTopColor ?? t.highAreaColor, t.highAreaTopColor, t.highAreaBottomColor), l.fill(f(o, c)), l.fillStyle = this._areaStyle(e, t.areaBottomColor ?? t.lowAreaColor, t.lowAreaTopColor, t.lowAreaBottomColor), l.fill(f(s, c))), this._strokeLine(e, s, t.lowLineVisible, t.lowLineColor, t.lowLineWidth, t.lowLineStyle), this._strokeLine(e, o, t.highLineVisible, t.highLineColor, t.highLineWidth, t.highLineStyle), this._strokeLine(e, c, t.closeLineVisible, t.closeLineColor, t.closeLineWidth, t.closeLineStyle);
	}
	_strokeLine(e, t, n, r, i, a) {
		if (!n) return;
		let o = e.context;
		o.strokeStyle = r, o.lineWidth = i * e.horizontalPixelRatio, g(o, a), o.stroke(t.path), o.setLineDash([]);
	}
	_areaStyle(e, t, n, r) {
		if (n === "" || r === "") return t;
		let i = e.context.createLinearGradient(0, 0, 0, e.bitmapSize.height);
		return i.addColorStop(0, n), i.addColorStop(1, r), i;
	}
	_drawHoverPoints(e, t, n, r) {
		let i = t.hoverPointRadius;
		if (i <= 0) return;
		let a = n.find((e) => e.index === r);
		if (a === void 0) return;
		let { context: o, horizontalPixelRatio: s, verticalPixelRatio: c } = e, l = a.x * s, u = [
			[a.high, t.highLineColor],
			[a.close, t.closeLineColor],
			[a.low, t.lowLineColor]
		];
		for (let [e, t] of u) o.beginPath(), o.fillStyle = t, o.arc(l, e * c, i * s, 0, Math.PI * 2), o.fill();
	}
}, x = class {
	_renderer;
	constructor(e) {
		this._renderer = new b(e);
	}
	priceValueBuilder(e) {
		return [
			e.low,
			e.high,
			e.close
		];
	}
	isWhitespace(e) {
		let t = e;
		return t.high === void 0 || t.low === void 0 || t.close === void 0;
	}
	renderer() {
		return this._renderer;
	}
	update(e, t) {
		this._renderer.update(e, t);
	}
	conflationReducer(e, t) {
		let n = e.data, r = t.data;
		return {
			...n,
			high: Math.max(n.high, r.high),
			low: Math.min(n.low, r.low),
			close: r.close
		};
	}
	defaultOptions() {
		return l;
	}
};
function S(e, t = {}, n = 0) {
	return c(e, (e) => new x(e), l, t, [], n);
}
//#endregion
export { x as HLCAreaSeries, S as createHLCAreaSeries, l as defaultOptions };
