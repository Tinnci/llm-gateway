// node_modules/@lit/reactive-element/css-tag.js
var t = globalThis;
var e = t.ShadowRoot && (t.ShadyCSS === undefined || t.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype;
var s = Symbol();
var o = new WeakMap;

class n {
  constructor(t2, e2, o2) {
    if (this._$cssResult$ = true, o2 !== s)
      throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t2, this.t = e2;
  }
  get styleSheet() {
    let t2 = this.o;
    const s2 = this.t;
    if (e && t2 === undefined) {
      const e2 = s2 !== undefined && s2.length === 1;
      e2 && (t2 = o.get(s2)), t2 === undefined && ((this.o = t2 = new CSSStyleSheet).replaceSync(this.cssText), e2 && o.set(s2, t2));
    }
    return t2;
  }
  toString() {
    return this.cssText;
  }
}
var r = (t2) => new n(typeof t2 == "string" ? t2 : t2 + "", undefined, s);
var i = (t2, ...e2) => {
  const o2 = t2.length === 1 ? t2[0] : e2.reduce((e3, s2, o3) => e3 + ((t3) => {
    if (t3._$cssResult$ === true)
      return t3.cssText;
    if (typeof t3 == "number")
      return t3;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + t3 + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s2) + t2[o3 + 1], t2[0]);
  return new n(o2, t2, s);
};
var S = (s2, o2) => {
  if (e)
    s2.adoptedStyleSheets = o2.map((t2) => t2 instanceof CSSStyleSheet ? t2 : t2.styleSheet);
  else
    for (const e2 of o2) {
      const o3 = document.createElement("style"), n2 = t.litNonce;
      n2 !== undefined && o3.setAttribute("nonce", n2), o3.textContent = e2.cssText, s2.appendChild(o3);
    }
};
var c = e ? (t2) => t2 : (t2) => t2 instanceof CSSStyleSheet ? ((t3) => {
  let e2 = "";
  for (const s2 of t3.cssRules)
    e2 += s2.cssText;
  return r(e2);
})(t2) : t2;

// node_modules/@lit/reactive-element/reactive-element.js
var { is: i2, defineProperty: e2, getOwnPropertyDescriptor: h, getOwnPropertyNames: r2, getOwnPropertySymbols: o2, getPrototypeOf: n2 } = Object;
var a = globalThis;
var c2 = a.trustedTypes;
var l = c2 ? c2.emptyScript : "";
var p = a.reactiveElementPolyfillSupport;
var d = (t2, s2) => t2;
var u = { toAttribute(t2, s2) {
  switch (s2) {
    case Boolean:
      t2 = t2 ? l : null;
      break;
    case Object:
    case Array:
      t2 = t2 == null ? t2 : JSON.stringify(t2);
  }
  return t2;
}, fromAttribute(t2, s2) {
  let i3 = t2;
  switch (s2) {
    case Boolean:
      i3 = t2 !== null;
      break;
    case Number:
      i3 = t2 === null ? null : Number(t2);
      break;
    case Object:
    case Array:
      try {
        i3 = JSON.parse(t2);
      } catch (t3) {
        i3 = null;
      }
  }
  return i3;
} };
var f = (t2, s2) => !i2(t2, s2);
var b = { attribute: true, type: String, converter: u, reflect: false, useDefault: false, hasChanged: f };
Symbol.metadata ??= Symbol("metadata"), a.litPropertyMetadata ??= new WeakMap;

class y extends HTMLElement {
  static addInitializer(t2) {
    this._$Ei(), (this.l ??= []).push(t2);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t2, s2 = b) {
    if (s2.state && (s2.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t2) && ((s2 = Object.create(s2)).wrapped = true), this.elementProperties.set(t2, s2), !s2.noAccessor) {
      const i3 = Symbol(), h2 = this.getPropertyDescriptor(t2, i3, s2);
      h2 !== undefined && e2(this.prototype, t2, h2);
    }
  }
  static getPropertyDescriptor(t2, s2, i3) {
    const { get: e3, set: r3 } = h(this.prototype, t2) ?? { get() {
      return this[s2];
    }, set(t3) {
      this[s2] = t3;
    } };
    return { get: e3, set(s3) {
      const h2 = e3?.call(this);
      r3?.call(this, s3), this.requestUpdate(t2, h2, i3);
    }, configurable: true, enumerable: true };
  }
  static getPropertyOptions(t2) {
    return this.elementProperties.get(t2) ?? b;
  }
  static _$Ei() {
    if (this.hasOwnProperty(d("elementProperties")))
      return;
    const t2 = n2(this);
    t2.finalize(), t2.l !== undefined && (this.l = [...t2.l]), this.elementProperties = new Map(t2.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(d("finalized")))
      return;
    if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d("properties"))) {
      const t3 = this.properties, s2 = [...r2(t3), ...o2(t3)];
      for (const i3 of s2)
        this.createProperty(i3, t3[i3]);
    }
    const t2 = this[Symbol.metadata];
    if (t2 !== null) {
      const s2 = litPropertyMetadata.get(t2);
      if (s2 !== undefined)
        for (const [t3, i3] of s2)
          this.elementProperties.set(t3, i3);
    }
    this._$Eh = new Map;
    for (const [t3, s2] of this.elementProperties) {
      const i3 = this._$Eu(t3, s2);
      i3 !== undefined && this._$Eh.set(i3, t3);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(s2) {
    const i3 = [];
    if (Array.isArray(s2)) {
      const e3 = new Set(s2.flat(1 / 0).reverse());
      for (const s3 of e3)
        i3.unshift(c(s3));
    } else
      s2 !== undefined && i3.push(c(s2));
    return i3;
  }
  static _$Eu(t2, s2) {
    const i3 = s2.attribute;
    return i3 === false ? undefined : typeof i3 == "string" ? i3 : typeof t2 == "string" ? t2.toLowerCase() : undefined;
  }
  constructor() {
    super(), this._$Ep = undefined, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise((t2) => this.enableUpdating = t2), this._$AL = new Map, this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((t2) => t2(this));
  }
  addController(t2) {
    (this._$EO ??= new Set).add(t2), this.renderRoot !== undefined && this.isConnected && t2.hostConnected?.();
  }
  removeController(t2) {
    this._$EO?.delete(t2);
  }
  _$E_() {
    const t2 = new Map, s2 = this.constructor.elementProperties;
    for (const i3 of s2.keys())
      this.hasOwnProperty(i3) && (t2.set(i3, this[i3]), delete this[i3]);
    t2.size > 0 && (this._$Ep = t2);
  }
  createRenderRoot() {
    const t2 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return S(t2, this.constructor.elementStyles), t2;
  }
  connectedCallback() {
    this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(true), this._$EO?.forEach((t2) => t2.hostConnected?.());
  }
  enableUpdating(t2) {}
  disconnectedCallback() {
    this._$EO?.forEach((t2) => t2.hostDisconnected?.());
  }
  attributeChangedCallback(t2, s2, i3) {
    this._$AK(t2, i3);
  }
  _$ET(t2, s2) {
    const i3 = this.constructor.elementProperties.get(t2), e3 = this.constructor._$Eu(t2, i3);
    if (e3 !== undefined && i3.reflect === true) {
      const h2 = (i3.converter?.toAttribute !== undefined ? i3.converter : u).toAttribute(s2, i3.type);
      this._$Em = t2, h2 == null ? this.removeAttribute(e3) : this.setAttribute(e3, h2), this._$Em = null;
    }
  }
  _$AK(t2, s2) {
    const i3 = this.constructor, e3 = i3._$Eh.get(t2);
    if (e3 !== undefined && this._$Em !== e3) {
      const t3 = i3.getPropertyOptions(e3), h2 = typeof t3.converter == "function" ? { fromAttribute: t3.converter } : t3.converter?.fromAttribute !== undefined ? t3.converter : u;
      this._$Em = e3;
      const r3 = h2.fromAttribute(s2, t3.type);
      this[e3] = r3 ?? this._$Ej?.get(e3) ?? r3, this._$Em = null;
    }
  }
  requestUpdate(t2, s2, i3, e3 = false, h2) {
    if (t2 !== undefined) {
      const r3 = this.constructor;
      if (e3 === false && (h2 = this[t2]), i3 ??= r3.getPropertyOptions(t2), !((i3.hasChanged ?? f)(h2, s2) || i3.useDefault && i3.reflect && h2 === this._$Ej?.get(t2) && !this.hasAttribute(r3._$Eu(t2, i3))))
        return;
      this.C(t2, s2, i3);
    }
    this.isUpdatePending === false && (this._$ES = this._$EP());
  }
  C(t2, s2, { useDefault: i3, reflect: e3, wrapped: h2 }, r3) {
    i3 && !(this._$Ej ??= new Map).has(t2) && (this._$Ej.set(t2, r3 ?? s2 ?? this[t2]), h2 !== true || r3 !== undefined) || (this._$AL.has(t2) || (this.hasUpdated || i3 || (s2 = undefined), this._$AL.set(t2, s2)), e3 === true && this._$Em !== t2 && (this._$Eq ??= new Set).add(t2));
  }
  async _$EP() {
    this.isUpdatePending = true;
    try {
      await this._$ES;
    } catch (t3) {
      Promise.reject(t3);
    }
    const t2 = this.scheduleUpdate();
    return t2 != null && await t2, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending)
      return;
    if (!this.hasUpdated) {
      if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
        for (const [t4, s3] of this._$Ep)
          this[t4] = s3;
        this._$Ep = undefined;
      }
      const t3 = this.constructor.elementProperties;
      if (t3.size > 0)
        for (const [s3, i3] of t3) {
          const { wrapped: t4 } = i3, e3 = this[s3];
          t4 !== true || this._$AL.has(s3) || e3 === undefined || this.C(s3, undefined, i3, e3);
        }
    }
    let t2 = false;
    const s2 = this._$AL;
    try {
      t2 = this.shouldUpdate(s2), t2 ? (this.willUpdate(s2), this._$EO?.forEach((t3) => t3.hostUpdate?.()), this.update(s2)) : this._$EM();
    } catch (s3) {
      throw t2 = false, this._$EM(), s3;
    }
    t2 && this._$AE(s2);
  }
  willUpdate(t2) {}
  _$AE(t2) {
    this._$EO?.forEach((t3) => t3.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t2)), this.updated(t2);
  }
  _$EM() {
    this._$AL = new Map, this.isUpdatePending = false;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t2) {
    return true;
  }
  update(t2) {
    this._$Eq &&= this._$Eq.forEach((t3) => this._$ET(t3, this[t3])), this._$EM();
  }
  updated(t2) {}
  firstUpdated(t2) {}
}
y.elementStyles = [], y.shadowRootOptions = { mode: "open" }, y[d("elementProperties")] = new Map, y[d("finalized")] = new Map, p?.({ ReactiveElement: y }), (a.reactiveElementVersions ??= []).push("2.1.2");

// node_modules/lit-html/lit-html.js
var t2 = globalThis;
var i3 = (t3) => t3;
var s2 = t2.trustedTypes;
var e3 = s2 ? s2.createPolicy("lit-html", { createHTML: (t3) => t3 }) : undefined;
var h2 = "$lit$";
var o3 = `lit$${Math.random().toFixed(9).slice(2)}$`;
var n3 = "?" + o3;
var r3 = `<${n3}>`;
var l2 = document;
var c3 = () => l2.createComment("");
var a2 = (t3) => t3 === null || typeof t3 != "object" && typeof t3 != "function";
var u2 = Array.isArray;
var d2 = (t3) => u2(t3) || typeof t3?.[Symbol.iterator] == "function";
var f2 = `[ 	
\f\r]`;
var v = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g;
var _ = /-->/g;
var m = />/g;
var p2 = RegExp(`>|${f2}(?:([^\\s"'>=/]+)(${f2}*=${f2}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g");
var g = /'/g;
var $ = /"/g;
var y2 = /^(?:script|style|textarea|title)$/i;
var x = (t3) => (i4, ...s3) => ({ _$litType$: t3, strings: i4, values: s3 });
var b2 = x(1);
var w = x(2);
var T = x(3);
var E = Symbol.for("lit-noChange");
var A = Symbol.for("lit-nothing");
var C = new WeakMap;
var P = l2.createTreeWalker(l2, 129);
function V(t3, i4) {
  if (!u2(t3) || !t3.hasOwnProperty("raw"))
    throw Error("invalid template strings array");
  return e3 !== undefined ? e3.createHTML(i4) : i4;
}
var N = (t3, i4) => {
  const s3 = t3.length - 1, e4 = [];
  let n4, l3 = i4 === 2 ? "<svg>" : i4 === 3 ? "<math>" : "", c4 = v;
  for (let i5 = 0;i5 < s3; i5++) {
    const s4 = t3[i5];
    let a3, u3, d3 = -1, f3 = 0;
    for (;f3 < s4.length && (c4.lastIndex = f3, u3 = c4.exec(s4), u3 !== null); )
      f3 = c4.lastIndex, c4 === v ? u3[1] === "!--" ? c4 = _ : u3[1] !== undefined ? c4 = m : u3[2] !== undefined ? (y2.test(u3[2]) && (n4 = RegExp("</" + u3[2], "g")), c4 = p2) : u3[3] !== undefined && (c4 = p2) : c4 === p2 ? u3[0] === ">" ? (c4 = n4 ?? v, d3 = -1) : u3[1] === undefined ? d3 = -2 : (d3 = c4.lastIndex - u3[2].length, a3 = u3[1], c4 = u3[3] === undefined ? p2 : u3[3] === '"' ? $ : g) : c4 === $ || c4 === g ? c4 = p2 : c4 === _ || c4 === m ? c4 = v : (c4 = p2, n4 = undefined);
    const x2 = c4 === p2 && t3[i5 + 1].startsWith("/>") ? " " : "";
    l3 += c4 === v ? s4 + r3 : d3 >= 0 ? (e4.push(a3), s4.slice(0, d3) + h2 + s4.slice(d3) + o3 + x2) : s4 + o3 + (d3 === -2 ? i5 : x2);
  }
  return [V(t3, l3 + (t3[s3] || "<?>") + (i4 === 2 ? "</svg>" : i4 === 3 ? "</math>" : "")), e4];
};

class S2 {
  constructor({ strings: t3, _$litType$: i4 }, e4) {
    let r4;
    this.parts = [];
    let l3 = 0, a3 = 0;
    const u3 = t3.length - 1, d3 = this.parts, [f3, v2] = N(t3, i4);
    if (this.el = S2.createElement(f3, e4), P.currentNode = this.el.content, i4 === 2 || i4 === 3) {
      const t4 = this.el.content.firstChild;
      t4.replaceWith(...t4.childNodes);
    }
    for (;(r4 = P.nextNode()) !== null && d3.length < u3; ) {
      if (r4.nodeType === 1) {
        if (r4.hasAttributes())
          for (const t4 of r4.getAttributeNames())
            if (t4.endsWith(h2)) {
              const i5 = v2[a3++], s3 = r4.getAttribute(t4).split(o3), e5 = /([.?@])?(.*)/.exec(i5);
              d3.push({ type: 1, index: l3, name: e5[2], strings: s3, ctor: e5[1] === "." ? I : e5[1] === "?" ? L : e5[1] === "@" ? z : H }), r4.removeAttribute(t4);
            } else
              t4.startsWith(o3) && (d3.push({ type: 6, index: l3 }), r4.removeAttribute(t4));
        if (y2.test(r4.tagName)) {
          const t4 = r4.textContent.split(o3), i5 = t4.length - 1;
          if (i5 > 0) {
            r4.textContent = s2 ? s2.emptyScript : "";
            for (let s3 = 0;s3 < i5; s3++)
              r4.append(t4[s3], c3()), P.nextNode(), d3.push({ type: 2, index: ++l3 });
            r4.append(t4[i5], c3());
          }
        }
      } else if (r4.nodeType === 8)
        if (r4.data === n3)
          d3.push({ type: 2, index: l3 });
        else {
          let t4 = -1;
          for (;(t4 = r4.data.indexOf(o3, t4 + 1)) !== -1; )
            d3.push({ type: 7, index: l3 }), t4 += o3.length - 1;
        }
      l3++;
    }
  }
  static createElement(t3, i4) {
    const s3 = l2.createElement("template");
    return s3.innerHTML = t3, s3;
  }
}
function M(t3, i4, s3 = t3, e4) {
  if (i4 === E)
    return i4;
  let h3 = e4 !== undefined ? s3._$Co?.[e4] : s3._$Cl;
  const o4 = a2(i4) ? undefined : i4._$litDirective$;
  return h3?.constructor !== o4 && (h3?._$AO?.(false), o4 === undefined ? h3 = undefined : (h3 = new o4(t3), h3._$AT(t3, s3, e4)), e4 !== undefined ? (s3._$Co ??= [])[e4] = h3 : s3._$Cl = h3), h3 !== undefined && (i4 = M(t3, h3._$AS(t3, i4.values), h3, e4)), i4;
}

class R {
  constructor(t3, i4) {
    this._$AV = [], this._$AN = undefined, this._$AD = t3, this._$AM = i4;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t3) {
    const { el: { content: i4 }, parts: s3 } = this._$AD, e4 = (t3?.creationScope ?? l2).importNode(i4, true);
    P.currentNode = e4;
    let h3 = P.nextNode(), o4 = 0, n4 = 0, r4 = s3[0];
    for (;r4 !== undefined; ) {
      if (o4 === r4.index) {
        let i5;
        r4.type === 2 ? i5 = new k(h3, h3.nextSibling, this, t3) : r4.type === 1 ? i5 = new r4.ctor(h3, r4.name, r4.strings, this, t3) : r4.type === 6 && (i5 = new Z(h3, this, t3)), this._$AV.push(i5), r4 = s3[++n4];
      }
      o4 !== r4?.index && (h3 = P.nextNode(), o4++);
    }
    return P.currentNode = l2, e4;
  }
  p(t3) {
    let i4 = 0;
    for (const s3 of this._$AV)
      s3 !== undefined && (s3.strings !== undefined ? (s3._$AI(t3, s3, i4), i4 += s3.strings.length - 2) : s3._$AI(t3[i4])), i4++;
  }
}

class k {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(t3, i4, s3, e4) {
    this.type = 2, this._$AH = A, this._$AN = undefined, this._$AA = t3, this._$AB = i4, this._$AM = s3, this.options = e4, this._$Cv = e4?.isConnected ?? true;
  }
  get parentNode() {
    let t3 = this._$AA.parentNode;
    const i4 = this._$AM;
    return i4 !== undefined && t3?.nodeType === 11 && (t3 = i4.parentNode), t3;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t3, i4 = this) {
    t3 = M(this, t3, i4), a2(t3) ? t3 === A || t3 == null || t3 === "" ? (this._$AH !== A && this._$AR(), this._$AH = A) : t3 !== this._$AH && t3 !== E && this._(t3) : t3._$litType$ !== undefined ? this.$(t3) : t3.nodeType !== undefined ? this.T(t3) : d2(t3) ? this.k(t3) : this._(t3);
  }
  O(t3) {
    return this._$AA.parentNode.insertBefore(t3, this._$AB);
  }
  T(t3) {
    this._$AH !== t3 && (this._$AR(), this._$AH = this.O(t3));
  }
  _(t3) {
    this._$AH !== A && a2(this._$AH) ? this._$AA.nextSibling.data = t3 : this.T(l2.createTextNode(t3)), this._$AH = t3;
  }
  $(t3) {
    const { values: i4, _$litType$: s3 } = t3, e4 = typeof s3 == "number" ? this._$AC(t3) : (s3.el === undefined && (s3.el = S2.createElement(V(s3.h, s3.h[0]), this.options)), s3);
    if (this._$AH?._$AD === e4)
      this._$AH.p(i4);
    else {
      const t4 = new R(e4, this), s4 = t4.u(this.options);
      t4.p(i4), this.T(s4), this._$AH = t4;
    }
  }
  _$AC(t3) {
    let i4 = C.get(t3.strings);
    return i4 === undefined && C.set(t3.strings, i4 = new S2(t3)), i4;
  }
  k(t3) {
    u2(this._$AH) || (this._$AH = [], this._$AR());
    const i4 = this._$AH;
    let s3, e4 = 0;
    for (const h3 of t3)
      e4 === i4.length ? i4.push(s3 = new k(this.O(c3()), this.O(c3()), this, this.options)) : s3 = i4[e4], s3._$AI(h3), e4++;
    e4 < i4.length && (this._$AR(s3 && s3._$AB.nextSibling, e4), i4.length = e4);
  }
  _$AR(t3 = this._$AA.nextSibling, s3) {
    for (this._$AP?.(false, true, s3);t3 !== this._$AB; ) {
      const s4 = i3(t3).nextSibling;
      i3(t3).remove(), t3 = s4;
    }
  }
  setConnected(t3) {
    this._$AM === undefined && (this._$Cv = t3, this._$AP?.(t3));
  }
}

class H {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t3, i4, s3, e4, h3) {
    this.type = 1, this._$AH = A, this._$AN = undefined, this.element = t3, this.name = i4, this._$AM = e4, this.options = h3, s3.length > 2 || s3[0] !== "" || s3[1] !== "" ? (this._$AH = Array(s3.length - 1).fill(new String), this.strings = s3) : this._$AH = A;
  }
  _$AI(t3, i4 = this, s3, e4) {
    const h3 = this.strings;
    let o4 = false;
    if (h3 === undefined)
      t3 = M(this, t3, i4, 0), o4 = !a2(t3) || t3 !== this._$AH && t3 !== E, o4 && (this._$AH = t3);
    else {
      const e5 = t3;
      let n4, r4;
      for (t3 = h3[0], n4 = 0;n4 < h3.length - 1; n4++)
        r4 = M(this, e5[s3 + n4], i4, n4), r4 === E && (r4 = this._$AH[n4]), o4 ||= !a2(r4) || r4 !== this._$AH[n4], r4 === A ? t3 = A : t3 !== A && (t3 += (r4 ?? "") + h3[n4 + 1]), this._$AH[n4] = r4;
    }
    o4 && !e4 && this.j(t3);
  }
  j(t3) {
    t3 === A ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t3 ?? "");
  }
}

class I extends H {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t3) {
    this.element[this.name] = t3 === A ? undefined : t3;
  }
}

class L extends H {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t3) {
    this.element.toggleAttribute(this.name, !!t3 && t3 !== A);
  }
}

class z extends H {
  constructor(t3, i4, s3, e4, h3) {
    super(t3, i4, s3, e4, h3), this.type = 5;
  }
  _$AI(t3, i4 = this) {
    if ((t3 = M(this, t3, i4, 0) ?? A) === E)
      return;
    const s3 = this._$AH, e4 = t3 === A && s3 !== A || t3.capture !== s3.capture || t3.once !== s3.once || t3.passive !== s3.passive, h3 = t3 !== A && (s3 === A || e4);
    e4 && this.element.removeEventListener(this.name, this, s3), h3 && this.element.addEventListener(this.name, this, t3), this._$AH = t3;
  }
  handleEvent(t3) {
    typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, t3) : this._$AH.handleEvent(t3);
  }
}

class Z {
  constructor(t3, i4, s3) {
    this.element = t3, this.type = 6, this._$AN = undefined, this._$AM = i4, this.options = s3;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t3) {
    M(this, t3);
  }
}
var B = t2.litHtmlPolyfillSupport;
B?.(S2, k), (t2.litHtmlVersions ??= []).push("3.3.3");
var D = (t3, i4, s3) => {
  const e4 = s3?.renderBefore ?? i4;
  let h3 = e4._$litPart$;
  if (h3 === undefined) {
    const t4 = s3?.renderBefore ?? null;
    e4._$litPart$ = h3 = new k(i4.insertBefore(c3(), t4), t4, undefined, s3 ?? {});
  }
  return h3._$AI(t3), h3;
};
// node_modules/lit-element/lit-element.js
var s3 = globalThis;

class i4 extends y {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = undefined;
  }
  createRenderRoot() {
    const t3 = super.createRenderRoot();
    return this.renderOptions.renderBefore ??= t3.firstChild, t3;
  }
  update(t3) {
    const r4 = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t3), this._$Do = D(r4, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(true);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(false);
  }
  render() {
    return E;
  }
}
i4._$litElement$ = true, i4["finalized"] = true, s3.litElementHydrateSupport?.({ LitElement: i4 });
var o4 = s3.litElementPolyfillSupport;
o4?.({ LitElement: i4 });
(s3.litElementVersions ??= []).push("4.2.2");
// custom_components/llm_gateway/frontend/voice-harness-audio-settings.ts
async function voiceSettingsRequest(hass, action, data = {}) {
  if (!hass.callApi)
    throw new Error("Home Assistant is unavailable");
  const service = action === "preview" ? "kukui_voice_audio_preview" : action === "pause" || action === "resume" ? `kukui_voice_${action}` : `kukui_voice_config_${action}`;
  const response = await hass.callApi("POST", `services/rest_command/${service}?return_response`, data);
  const result = response.service_response;
  if (result?.content?.ok !== true || result.status !== 200) {
    throw new Error(result?.content?.error || "The satellite did not apply this request");
  }
  if (action === "preview" && !["played", "muted"].includes(result.content.status || "")) {
    throw new Error("Test sound playback was not confirmed");
  }
  if (action === "read" || action === "update") {
    const config = result.content.config;
    if (!config || typeof config !== "object" || Array.isArray(config)) {
      throw new Error("The satellite did not return its settings");
    }
    return { ...result.content, config: Object.fromEntries(Object.entries(config).filter(([, value]) => typeof value === "boolean" || typeof value === "number" && Number.isFinite(value))) };
  }
  return result.content;
}

class VoiceSettingsSaver {
  save;
  changed;
  pending = {};
  saved = {};
  error = "";
  saving = false;
  inflight = {};
  applied = false;
  timer;
  flight;
  constructor(save, changed) {
    this.save = save;
    this.changed = changed;
  }
  edit(field, value) {
    this.editPatch({ [field]: value });
  }
  editPatch(patch) {
    this.pending = { ...this.pending, ...patch };
    this.error = "";
    this.applied = false;
    clearTimeout(this.timer);
    this.timer = setTimeout(() => void this.flush().catch(() => {}), 400);
    this.changed();
  }
  flush(reapply = false) {
    clearTimeout(this.timer);
    if (this.flight)
      return this.flight;
    const run = async () => {
      while (Object.keys(this.pending).length || reapply) {
        reapply = false;
        const patch = this.pending;
        this.inflight = patch;
        this.pending = {};
        this.saving = true;
        this.changed();
        try {
          const response = await this.save({ ...patch });
          if (!response.ok || !response.apply?.applied || !response.config) {
            throw new Error(response.error || "Settings were saved but could not be applied");
          }
          this.saved = { ...response.config };
          this.applied = true;
          this.error = "";
        } catch (error) {
          this.pending = { ...patch, ...this.pending };
          this.error = error instanceof Error ? error.message : String(error);
          this.applied = false;
          throw error;
        } finally {
          this.saving = false;
          this.inflight = {};
          this.changed();
        }
      }
    };
    this.flight = run().finally(() => {
      this.flight = undefined;
    });
    return this.flight;
  }
}
var groups = [
  { title: ["Wake and follow-up", "唤醒与追问"], fields: [
    ["wake_cue_volume", "Wake cue", "唤醒提示音", 0.05, 0.7, 1],
    ["follow_up_cue_volume", "Follow-up cue", "追问提示音", 0.05, 0.7, 1]
  ] },
  { title: ["Spoken replies", "语音播报"], fields: [
    ["tts_volume_day", "Daytime speech", "日间播报", 0.2, 0.7, 1],
    ["tts_volume_night", "Nighttime speech", "夜间播报", 0.2, 0.5, 0.75]
  ] },
  { title: ["Gentle feedback", "轻声反馈"], fields: [
    ["processing_volume", "Thinking", "思考等待音", 0.05, 0.45, 0.65],
    ["fallback_volume", "Completion and errors", "完成与错误提示", 0.2, 0.6, 1]
  ] }
];
var audioScenes = [
  { id: "daily", name: ["Everyday", "日常"], hint: ["Clear and present", "清晰、自然"], values: {
    wake_cue_volume: 1,
    follow_up_cue_volume: 1,
    processing_volume: 0.58,
    tts_volume_day: 1,
    tts_volume_night: 0.72,
    fallback_volume: 1,
    night_mode: false
  } },
  { id: "focus", name: ["Focus", "专注"], hint: ["Less interruption", "减少打扰"], values: {
    wake_cue_volume: 0.7,
    follow_up_cue_volume: 0.75,
    processing_volume: 0.25,
    tts_volume_day: 0.85,
    tts_volume_night: 0.6,
    fallback_volume: 0.7,
    night_mode: false
  } },
  { id: "night", name: ["Quiet night", "夜间"], hint: ["Softer cues and speech", "提示与播报更柔和"], values: {
    wake_cue_volume: 0.55,
    follow_up_cue_volume: 0.6,
    processing_volume: 0.2,
    tts_volume_day: 1,
    tts_volume_night: 0.72,
    fallback_volume: 0.55,
    night_mode: true
  } }
];

class VoiceHarnessAudioSettings extends i4 {
  static properties = { hass: { attribute: false }, language: { type: String } };
  loaded = false;
  loadError = "";
  previewing = "";
  previewMessage = "";
  controllingCapture = false;
  runtime;
  readFlight;
  poll;
  onVisibility = () => {
    if (document.visibilityState !== "hidden")
      this.refresh();
  };
  saver = new VoiceSettingsSaver(async (patch) => {
    const response = await voiceSettingsRequest(this.hass, "update", { config: patch });
    this.runtime = response.runtime;
    this.loadError = "";
    this.loaded = true;
    return response;
  }, () => this.requestUpdate());
  setConfig() {}
  getCardSize() {
    return 10;
  }
  connectedCallback() {
    super.connectedCallback();
    document.addEventListener("visibilitychange", this.onVisibility);
    this.poll = setInterval(() => void this.refresh(), 2000);
    this.refresh();
  }
  updated(changes) {
    if (changes.has("hass") && this.hass && !this.loaded)
      this.refresh();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    clearInterval(this.poll);
    document.removeEventListener("visibilitychange", this.onVisibility);
    this.saver.flush().catch(() => {});
  }
  refresh() {
    if (this.readFlight)
      return this.readFlight;
    if (!this.hass?.callApi || this.saver.saving || document.visibilityState === "hidden")
      return Promise.resolve();
    const savedBeforeRead = this.saver.saved;
    this.readFlight = (async () => {
      try {
        const response = await voiceSettingsRequest(this.hass, "read");
        if (this.saver.saving || this.saver.saved !== savedBeforeRead)
          return;
        this.saver.saved = { ...response.config };
        this.saver.applied = response.apply?.applied === true;
        this.runtime = response.runtime;
        this.loaded = true;
        this.loadError = "";
      } catch (error) {
        if (this.saver.saved === savedBeforeRead)
          this.loadError = String(error);
      } finally {
        this.readFlight = undefined;
        this.requestUpdate();
      }
    })();
    return this.readFlight;
  }
  text(en, zh) {
    return (this.language || this.hass?.language || "en").startsWith("zh") ? zh : en;
  }
  async preview(field) {
    this.previewing = field;
    this.previewMessage = this.text("Requesting a test sound on the tablet…", "正在请求平板试听…");
    this.requestUpdate();
    try {
      await this.saver.flush(!this.saver.applied);
      const response = await voiceSettingsRequest(this.hass, "preview", { field });
      this.previewMessage = response.status === "muted" ? this.text("Speaker muted. Your volume settings are kept.", "扬声器已静音，音量设置已保留。") : this.text("Tablet test playback completed", "平板试听播放完成");
    } catch (error) {
      this.previewMessage = `${this.text("Test sound not completed", "试听未完成")} · ${error instanceof Error ? error.message : String(error)}`;
    } finally {
      this.previewing = "";
      this.requestUpdate();
    }
  }
  async toggleCapture() {
    this.controllingCapture = true;
    this.requestUpdate();
    try {
      await voiceSettingsRequest(this.hass, this.runtime?.capture === "paused" ? "resume" : "pause", { seconds: 1800, reason: "audio_settings" });
      await this.refresh();
    } catch (error) {
      this.previewMessage = `${this.text("Wake control not confirmed", "唤醒控制未确认")} · ${String(error)}`;
    } finally {
      this.controllingCapture = false;
      this.requestUpdate();
    }
  }
  captureLabel() {
    switch (this.runtime?.capture) {
      case "listening":
        return this.text("Listening to you", "正在聆听你");
      case "closed":
        return this.text("Recording ended", "本轮收音已结束");
      case "wake_word":
        return this.text("Ready for the wake word", "等待唤醒词");
      case "paused":
        return this.text("Wake word paused", "唤醒已暂停");
      default:
        return this.text("Capture state unavailable", "收音状态未知");
    }
  }
  render() {
    const values = { ...this.saver.saved, ...this.saver.inflight, ...this.saver.pending };
    const pending = Object.keys(this.saver.pending).length > 0;
    const scene = audioScenes.find((item) => Object.entries(item.values).every(([key, value]) => values[key] === value));
    const busy = ["listening", "stt", "thinking", "speaking"].includes(this.runtime?.phase || "");
    const status = this.loadError ? this.text("Tablet connection interrupted", "平板连接中断") : !this.loaded ? this.text("Connecting to the tablet…", "正在连接平板…") : this.saver.error ? this.text("Application not confirmed", "应用未确认") : this.saver.saving ? this.text("Applying…", "正在应用…") : pending ? this.text("Saving…", "正在保存…") : this.saver.applied ? this.text("Synced with the tablet", "已同步到平板") : this.text("Saved · application pending", "已保存 · 等待应用");
    return b2`
      <section aria-label=${this.text("Tablet audio", "平板声音")}>
        <header><div><span class="eyebrow">${this.text("VOICE & SOUND", "语音与声音")}</span>
          <h2>${this.text("Tablet audio", "平板声音")}</h2><p role="status">${status}</p></div>
          <span class="profile">${this.runtime?.tts_profile === "night" ? this.text("Night speech", "夜间播报") : this.runtime?.tts_profile === "day" ? this.text("Day speech", "日间播报") : "—"}
            <strong>${!this.loadError && this.runtime?.tts_volume != null ? `${Math.round(this.runtime.tts_volume * 100)}%` : "—"}</strong></span></header>
        <div class="toggles">${[["audio_muted", "Speaker mute", "扬声器静音"], ["night_mode", "Use night volume", "使用夜间音量"]].map(([field, en, zh]) => b2`
          <button aria-pressed=${values[field] === true} ?disabled=${!this.loaded || typeof values[field] !== "boolean"}
            @click=${() => this.saver.edit(field, !values[field])}>${this.text(en, zh)}</button>`)}</div>
        <div class="capture"><span class=${this.runtime?.capture === "listening" && !this.loadError ? "listening" : ""}>${this.loadError ? this.text("Capture state unavailable", "收音状态未知") : this.captureLabel()}</span>
          <button ?disabled=${!this.loaded || !!this.loadError || this.controllingCapture || !this.runtime}
            @click=${() => this.toggleCapture()}>${this.controllingCapture ? this.text("Updating…", "正在处理…") : this.runtime?.capture === "paused" ? this.text("Resume wake word", "恢复唤醒") : this.text("Pause for 30 min", "免打扰 30 分钟")}</button></div>
        <p class="explanation">${this.text("Mute keeps the microphone available. Do not disturb pauses wake and capture.", "静音保留麦克风；免打扰暂停唤醒与收音。")}</p>
        <div class="section-label"><h3>${this.text("Sound for your moment", "适合此刻的声音")}</h3><span>${scene ? this.text(scene.name[0], scene.name[1]) : this.text("Custom", "自定义")}</span></div>
        <div class="scenes">${audioScenes.map((item) => b2`<button aria-pressed=${scene?.id === item.id}
          ?disabled=${!this.loaded} @click=${() => this.saver.editPatch(item.values)}>
          <strong>${this.text(item.name[0], item.name[1])}</strong><span>${this.text(item.hint[0], item.hint[1])}</span></button>`)}</div>
        <div class="groups">${groups.map((group) => b2`<fieldset><legend>${this.text(group.title[0], group.title[1])}</legend>
          ${group.fields.map(([field, en, zh, min, low, high]) => {
      const value = typeof values[field] === "number" ? values[field] : undefined;
      const active = this.previewing === field;
      return b2`<div class="volume-row" aria-busy=${active}>
              <label for=${field}>${this.text(en, zh)}<output for=${field}>${value == null ? "—" : `${Math.round(value * 100)}%`}</output></label>
              <div class="slider-row"><div class="range">
                <span class="recommended" aria-hidden="true" style=${`left:${(low - min) / (1 - min) * 100}%;width:${(high - low) / (1 - min) * 100}%`}></span>
                <input id=${field} type="range" min=${min} max="1" step="0.01" .value=${String(value ?? min)}
                  aria-valuetext=${value == null ? "—" : `${Math.round(value * 100)}%`}
                  ?disabled=${!this.loaded || value == null}
                  @input=${(event) => this.saver.edit(field, Number(event.target.value))}>
              </div><button class="preview" ?disabled=${!this.loaded || value == null || Boolean(this.previewing) || busy || !!this.loadError}
                aria-label=${`${this.text("Play test sound on tablet", "在平板试听")} · ${this.text(en, zh)}`}
                @click=${() => this.preview(field)}>
                ${active ? b2`<span class="wave" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>` : b2`<span aria-hidden="true">▶</span>`}
                <span>${active ? this.text("Testing…", "试听中…") : this.text("Test", "试听")}</span>
              </button></div>
              <p class="range-note">${this.text("Everyday range", "日常建议")} ${Math.round(low * 100)}–${Math.round(high * 100)}%</p>
            </div>`;
    })}</fieldset>`)}</div>
        <div class="headroom"><span class="peak-line" aria-hidden="true"></span><p>${this.text("Earcon master peak", "提示音母带峰值")} <strong>−1.0 dBFS</strong><br>
          ${this.text("100% is unity gain. Night speech is automatic from 22:00 to 07:00 on the tablet.", "100% 为原始增益。平板时间 22:00–07:00 自动使用夜间播报音量。")}</p></div>
        ${this.loadError ? b2`<div class="error" role="alert">${this.text("Cannot refresh tablet settings. Your edits are kept.", "暂时无法读取平板设置，修改仍会保留。")}
          <button @click=${() => this.refresh()}>${this.text("Reconnect", "重新连接")}</button></div>` : ""}
        ${this.saver.error || this.loaded && !this.saver.applied && !pending && !this.saver.saving ? b2`<div class="error" role="alert">${this.saver.error ? this.text("Changes are unconfirmed and kept for retry.", "修改尚未确认，已保留供重试。") : this.text("Saved settings need another application attempt.", "已保存的设置需要重新应用。")}
          <button @click=${() => void this.saver.flush(true).catch(() => {})}>${this.text("Retry", "重试")}</button></div>` : ""}
        <p class="preview-status" role="status">${this.previewMessage || (busy ? this.text("A conversation is active. Test sounds are available after the reply.", "正在对话，回复结束后可以试听。") : this.text("Test sounds play through the tablet speaker.", "试听声音从平板扬声器播放。"))}</p>
      </section>`;
  }
  static styles = i`
    :host { display: block; container-type: inline-size; color: var(--primary-text-color, #213b3b); --accent: var(--primary-color, #257a70); --surface: var(--card-background-color, #fff); --muted: var(--secondary-text-color, #637773); }
    * { box-sizing: border-box; }
    section { background: linear-gradient(145deg, color-mix(in srgb, var(--accent) 7%, var(--surface)), var(--surface) 45%); border: 1px solid var(--divider-color, #dfe7e3); border-radius: 26px; padding: 26px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 20px; }
    .eyebrow { color: var(--muted); font-size: 11px; letter-spacing: .14em; }
    h2 { font-size: 27px; font-weight: 550; margin: 7px 0 8px; letter-spacing: -.03em; }
    h3 { font-size: 14px; font-weight: 550; margin: 0; }
    p { color: var(--muted); font-size: 12px; line-height: 1.6; margin: 0; }
    .profile { color: var(--muted); font-size: 11px; text-align: right; white-space: nowrap; }
    .profile strong { display: block; color: var(--primary-text-color, #213b3b); font-size: 30px; font-weight: 450; font-variant-numeric: tabular-nums; }
    button { font: inherit; font-size: 13px; border: 1px solid var(--divider-color, #d6e2de); background: transparent; color: inherit; border-radius: 14px; min-height: 44px; min-width: 44px; padding: 10px 14px; cursor: pointer; transition: background .18s, transform .18s; touch-action: manipulation; }
    button:hover:enabled { background: color-mix(in srgb, var(--accent) 9%, transparent); }
    button:active:enabled { transform: scale(.98); }
    button:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
    button:disabled { opacity: .45; cursor: default; }
    button[aria-pressed=true] { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 12%, transparent); }
    .toggles { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 24px; }
    .capture { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 12px; font-size: 12px; color: var(--muted); }
    .capture > span::before { content: ''; display: inline-block; width: 6px; height: 6px; margin-right: 8px; background: currentColor; border-radius: 50%; }
    .capture .listening { color: var(--accent); }
    .capture .listening::before { animation: listen 1.2s ease-in-out infinite alternate; }
    .capture button { font-size: 12px; padding: 8px 10px; border-color: transparent; flex-shrink: 0; }
    .explanation { margin-top: 3px; font-size: 11px; }
    .section-label { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 26px 0 12px; }
    .section-label > span { font-size: 12px; color: var(--muted); }
    .scenes { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .scenes button { text-align: left; padding: 14px; }
    .scenes strong { display: block; font-size: 14px; font-weight: 550; }
    .scenes span { display: block; margin-top: 6px; font-size: 11px; color: var(--muted); line-height: 1.4; }
    .groups { display: grid; gap: 20px; margin-top: 28px; }
    fieldset { min-width: 0; margin: 0; padding: 14px 16px 2px; border: 1px solid var(--divider-color, #dfe7e3); border-radius: 18px; }
    legend { padding: 0 7px; font-size: 13px; font-weight: 550; color: var(--muted); }
    .volume-row { margin: 2px 0 16px; }
    label { display: flex; justify-content: space-between; gap: 12px; align-items: center; font-size: 14px; }
    output { font-size: 15px; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .slider-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 14px; align-items: center; margin-top: 3px; }
    .range { position: relative; height: 44px; }
    .recommended { position: absolute; height: 3px; bottom: 1px; border-radius: 2px; background: color-mix(in srgb, var(--accent) 35%, transparent); pointer-events: none; }
    input { display: block; width: 100%; min-width: 0; height: 44px; margin: 0; accent-color: var(--accent); cursor: pointer; }
    .preview { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-width: 82px; padding: 8px 11px; font-size: 12px; }
    .range-note { font-size: 10px; margin-top: 3px; }
    .headroom { display: flex; gap: 12px; align-items: center; margin-top: 22px; }
    .headroom p { font-size: 11px; }
    .headroom strong { font-weight: 500; white-space: nowrap; }
    .peak-line { width: 5px; height: 32px; flex-shrink: 0; border-radius: 3px; border-top: 2px solid var(--accent); background: color-mix(in srgb, var(--accent) 15%, transparent); }
    .error { display: flex; gap: 12px; align-items: center; justify-content: space-between; color: var(--error-color, #b84030); margin-top: 16px; font-size: 13px; }
    .preview-status { margin-top: 18px; min-height: 20px; }
    .wave { display: inline-flex; align-items: center; gap: 2px; height: 18px; }
    .wave i { display: block; background: currentColor; width: 2px; height: 12px; border-radius: 2px; animation: wave .6s ease-in-out infinite alternate; }
    .wave i:nth-child(2n) { animation-delay: -.25s; height: 18px; }
    .wave i:nth-child(3) { animation-delay: -.4s; }
    @keyframes wave { from { transform: scaleY(.3); } to { transform: scaleY(1); } }
    @keyframes listen { from { opacity: .4; } to { opacity: 1; } }
    @container (min-width: 700px) { .groups { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; } .preview > span:last-child { display: none; } .preview { min-width: 44px; } }
    @container (max-width: 430px) { section { padding: 20px 16px; border-radius: 20px; } h2 { font-size: 25px; } .scenes { gap: 7px; } .scenes button { padding: 12px 10px; } }
    @media (prefers-reduced-motion: reduce) { *, *::before { animation: none !important; transition: none !important; } }
  `;
}
if (!customElements.get("voice-harness-audio-settings")) {
  customElements.define("voice-harness-audio-settings", VoiceHarnessAudioSettings);
}

// custom_components/llm_gateway/frontend/voice-harness-styles.ts
var harnessFoundationStyles = i`
  :host {
    box-sizing: border-box;
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, inherit);
    --vh-radius-s: 7px;
    --vh-radius-m: 10px;
    --vh-space-xs: 4px;
    --vh-space-s: 8px;
    --vh-space-m: 12px;
  }

  *,
  *::before,
  *::after {
    box-sizing: inherit;
  }
`;
var harnessButtonStyles = i`
  button {
    min-height: 40px;
    border: 0;
    border-radius: var(--vh-radius-s);
    color: inherit;
    font: inherit;
    cursor: pointer;
  }

  button:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: -2px;
  }
`;

// custom_components/llm_gateway/frontend/voice-harness-navigation.ts
class VoiceHarnessNavigation extends i4 {
  static properties = {
    active: { type: String },
    items: { attribute: false }
  };
  constructor() {
    super();
    this.active = "";
    this.items = [];
  }
  render() {
    return b2`
      <nav aria-label="Voice Harness views" role="tablist">
        ${this.items.map((item) => b2`
            <button
              aria-selected=${String(item.id === this.active)}
              data-id=${item.id}
              role="tab"
              tabindex=${item.id === this.active ? "0" : "-1"}
              @click=${() => this.select(item.id)}
              @keydown=${this.onKeydown}
            >
              <ha-icon icon=${item.icon}></ha-icon>
              <span>${item.label}</span>
            </button>
          `)}
      </nav>
    `;
  }
  select(id) {
    this.dispatchEvent(new CustomEvent("harness-view-select", {
      bubbles: true,
      composed: true,
      detail: { id }
    }));
  }
  onKeydown(event) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      return;
    }
    event.preventDefault();
    const current = this.items.findIndex((item2) => item2.id === this.active);
    let next = current < 0 ? 0 : current;
    if (event.key === "Home")
      next = 0;
    if (event.key === "End")
      next = this.items.length - 1;
    if (event.key === "ArrowLeft")
      next = (next - 1 + this.items.length) % this.items.length;
    if (event.key === "ArrowRight")
      next = (next + 1) % this.items.length;
    const item = this.items[next];
    if (!item)
      return;
    this.select(item.id);
    const button = this.renderRoot.querySelector(`button[data-id="${CSS.escape(item.id)}"]`);
    button?.focus();
  }
  static styles = [harnessFoundationStyles, harnessButtonStyles, i`
    :host { display: block; margin: 14px 0 18px; }
    nav { display: flex; gap: var(--vh-space-xs); padding: var(--vh-space-xs); overflow-x: auto; border: 1px solid var(--divider-color); border-radius: var(--vh-radius-m); background: var(--card-background-color); }
    button { min-width: 0; flex: 1 0 132px; display: inline-flex; align-items: center; justify-content: center; gap: var(--vh-space-s); padding: 0 var(--vh-space-m); background: transparent; white-space: nowrap; }
    button:hover { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
    button[aria-selected="true"] { background: color-mix(in srgb, var(--primary-color) 14%, var(--card-background-color)); color: var(--primary-color); }
    ha-icon { width: 20px; height: 20px; flex: 0 0 auto; }
    span { min-width: 0; overflow: hidden; text-overflow: ellipsis; }
    @media (max-width: 560px) { button { flex-basis: 112px; justify-content: flex-start; } }
  `];
}
if (!customElements.get("voice-harness-navigation")) {
  customElements.define("voice-harness-navigation", VoiceHarnessNavigation);
}

// custom_components/llm_gateway/frontend/voice-harness-stat.ts
class VoiceHarnessStat extends i4 {
  static properties = {
    icon: { type: String },
    label: { type: String },
    tone: { reflect: true, type: String },
    value: { type: String }
  };
  constructor() {
    super();
    this.icon = "mdi:information-outline";
    this.label = "";
    this.tone = "muted";
    this.value = "";
  }
  render() {
    return b2`
      <ha-icon icon=${this.icon}></ha-icon>
      <div><span>${this.label}</span><strong>${this.value || "-"}</strong></div>
    `;
  }
  static styles = [harnessFoundationStyles, i`
    :host { min-height: 66px; display: grid; grid-template-columns: 26px minmax(0, 1fr); gap: 8px; align-items: center; padding: 10px; border: 1px solid var(--divider-color); border-radius: 8px; background: var(--card-background-color); box-sizing: border-box; }
    :host([tone="ok"]) { border-color: color-mix(in srgb, var(--success-color) 30%, var(--divider-color)); }
    :host([tone="warning"]) { border-color: color-mix(in srgb, var(--warning-color) 38%, var(--divider-color)); }
    :host([tone="bad"]) { border-color: color-mix(in srgb, var(--error-color) 38%, var(--divider-color)); }
    ha-icon { width: 22px; height: 22px; color: var(--secondary-text-color); }
    div { min-width: 0; display: grid; gap: 2px; }
    span { color: var(--secondary-text-color); font-size: 12px; overflow: hidden; text-overflow: ellipsis; }
    strong { min-width: 0; font-size: 14px; line-height: 1.25; overflow-wrap: anywhere; }
  `];
}
if (!customElements.get("voice-harness-stat")) {
  customElements.define("voice-harness-stat", VoiceHarnessStat);
}

// custom_components/llm_gateway/frontend/voice-harness-overview.ts
class VoiceHarnessOverview extends i4 {
  static properties = {
    model: { attribute: false },
    openSections: { attribute: false }
  };
  constructor() {
    super();
    this.model = null;
    this.openSections = [];
  }
  render() {
    const model = this.model;
    if (!model)
      return A;
    return b2`
      <section class="surface hero" aria-label=${model.ariaLabel}>
        <header>
          <div>
            <h2>${model.headline}</h2>
            <span class="meta">${model.statusLine}</span>
          </div>
          <span class="chip ${model.stateTone}">${model.stateLabel}</span>
        </header>
        <div class="metrics">
          ${model.metrics.map((metric) => b2`
              <voice-harness-stat
                .icon=${metric.icon}
                .label=${metric.label}
                .tone=${metric.tone}
                .value=${metric.value}
              ></voice-harness-stat>
            `)}
        </div>
        <div class="focus ${model.stateTone}">
          <ha-icon icon=${model.focusIcon}></ha-icon>
          <div>
            <strong>${model.focusTitle}</strong>
            <span>${model.focusHint}</span>
          </div>
          <div class="actions">
            ${model.actions.map((action) => b2`
                <button @click=${() => this.navigate(action.destination)}>
                  <ha-icon icon=${action.icon}></ha-icon>
                  <span>${action.label}</span>
                </button>
              `)}
          </div>
        </div>
      </section>
      <slot name="satellite"></slot>
      ${this.disclosure("diagnostics", model.diagnosticsLabel)}
      ${this.disclosure("memory", model.memoryLabel)}
    `;
  }
  disclosure(id, label) {
    return b2`
      <details
        class="surface disclosure"
        .open=${this.openSections.includes(id)}
        @toggle=${(event) => this.onToggle(id, event)}
      >
        <summary>${label}</summary>
        <slot name=${id}></slot>
      </details>
    `;
  }
  navigate(destination) {
    this.dispatchEvent(new CustomEvent("harness-overview-navigate", {
      bubbles: true,
      composed: true,
      detail: { destination }
    }));
  }
  onToggle(id, event) {
    const details = event.currentTarget;
    if (!(details instanceof HTMLDetailsElement))
      return;
    this.dispatchEvent(new CustomEvent("harness-overview-disclosure-toggle", {
      bubbles: true,
      composed: true,
      detail: { id, open: details.open }
    }));
  }
  static styles = [harnessFoundationStyles, harnessButtonStyles, i`
    :host { display: grid; gap: 14px; }
    .surface { background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 8px; }
    .hero { padding: 16px; }
    header { min-height: 42px; display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
    header > div { min-width: 0; }
    h2 { margin: 0 0 4px; font-size: 16px; }
    .meta { color: var(--secondary-text-color); font-size: 12px; line-height: 1.4; }
    .chip { display: inline-flex; align-items: center; min-height: 26px; padding: 0 9px; border: 1px solid var(--divider-color); border-radius: 999px; font-size: 11px; white-space: nowrap; }
    .chip.ok { color: var(--success-color); border-color: color-mix(in srgb, var(--success-color) 35%, var(--divider-color)); }
    .chip.warning { color: var(--warning-color); border-color: color-mix(in srgb, var(--warning-color) 42%, var(--divider-color)); }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
    .focus { min-height: 72px; display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; gap: 12px; align-items: center; margin-top: 12px; padding: 12px; border: 1px solid var(--divider-color); border-radius: 8px; background: var(--primary-background-color); }
    .focus.ok { border-color: color-mix(in srgb, var(--success-color) 30%, var(--divider-color)); }
    .focus.warning { border-color: color-mix(in srgb, var(--warning-color) 42%, var(--divider-color)); }
    .focus > ha-icon { width: 24px; height: 24px; color: var(--secondary-text-color); }
    .focus > div:nth-child(2) { min-width: 0; display: grid; gap: 4px; }
    .focus strong { font-size: 14px; }
    .focus span { color: var(--secondary-text-color); font-size: 12px; line-height: 1.4; }
    .actions { display: flex; gap: 8px; }
    button { display: inline-flex; align-items: center; gap: 8px; padding: 0 14px; background: var(--secondary-background-color); border: 1px solid var(--divider-color); }
    button:hover { background: color-mix(in srgb, var(--primary-color) 8%, var(--secondary-background-color)); }
    .disclosure { padding: 0; overflow: hidden; }
    summary { min-height: 48px; display: flex; align-items: center; padding: 0 16px; cursor: pointer; font-size: 14px; font-weight: 650; }
    details[open] > summary { border-bottom: 1px solid var(--divider-color); }
    ::slotted(.overview-slot) { display: block; margin: 14px; }
    slot[name="satellite"]::slotted(.overview-slot) { margin: 0; }
    @media (max-width: 900px) {
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .focus { grid-template-columns: 28px minmax(0, 1fr); }
      .actions { grid-column: 2; justify-content: flex-start; }
    }
    @media (max-width: 560px) {
      .metrics { grid-template-columns: 1fr; }
      .focus { grid-template-columns: 1fr; }
      .actions { grid-column: 1; flex-direction: column; }
      button { width: 100%; justify-content: center; }
    }
  `];
}
if (!customElements.get("voice-harness-overview")) {
  customElements.define("voice-harness-overview", VoiceHarnessOverview);
}
// node_modules/diff/libesm/diff/base.js
class Diff {
  diff(oldStr, newStr, options = {}) {
    let callback;
    if (typeof options === "function") {
      callback = options;
      options = {};
    } else if ("callback" in options) {
      callback = options.callback;
    }
    const oldString = this.castInput(oldStr, options);
    const newString = this.castInput(newStr, options);
    const oldTokens = this.removeEmpty(this.tokenize(oldString, options));
    const newTokens = this.removeEmpty(this.tokenize(newString, options));
    return this.diffWithOptionsObj(oldTokens, newTokens, options, callback);
  }
  diffWithOptionsObj(oldTokens, newTokens, options, callback) {
    var _a;
    const done = (value) => {
      value = this.postProcess(value, options);
      if (callback) {
        setTimeout(function() {
          callback(value);
        }, 0);
        return;
      } else {
        return value;
      }
    };
    const newLen = newTokens.length, oldLen = oldTokens.length;
    let editLength = 1;
    let maxEditLength = newLen + oldLen;
    if (options.maxEditLength != null) {
      maxEditLength = Math.min(maxEditLength, options.maxEditLength);
    }
    const maxExecutionTime = (_a = options.timeout) !== null && _a !== undefined ? _a : Infinity;
    const abortAfterTimestamp = Date.now() + maxExecutionTime;
    const bestPath = [{ oldPos: -1, lastComponent: undefined }];
    let newPos = this.extractCommon(bestPath[0], newTokens, oldTokens, 0, options);
    if (bestPath[0].oldPos + 1 >= oldLen && newPos + 1 >= newLen) {
      return done(this.buildValues(bestPath[0].lastComponent, newTokens, oldTokens));
    }
    let minDiagonalToConsider = -Infinity, maxDiagonalToConsider = Infinity;
    const execEditLength = () => {
      for (let diagonalPath = Math.max(minDiagonalToConsider, -editLength);diagonalPath <= Math.min(maxDiagonalToConsider, editLength); diagonalPath += 2) {
        let basePath;
        const removePath = bestPath[diagonalPath - 1], addPath = bestPath[diagonalPath + 1];
        if (removePath) {
          bestPath[diagonalPath - 1] = undefined;
        }
        let canAdd = false;
        if (addPath) {
          const addPathNewPos = addPath.oldPos - diagonalPath;
          canAdd = addPath && 0 <= addPathNewPos && addPathNewPos < newLen;
        }
        const canRemove = removePath && removePath.oldPos + 1 < oldLen;
        if (!canAdd && !canRemove) {
          bestPath[diagonalPath] = undefined;
          continue;
        }
        if (!canRemove || canAdd && removePath.oldPos < addPath.oldPos) {
          basePath = this.addToPath(addPath, true, false, 0, options);
        } else {
          basePath = this.addToPath(removePath, false, true, 1, options);
        }
        newPos = this.extractCommon(basePath, newTokens, oldTokens, diagonalPath, options);
        if (basePath.oldPos + 1 >= oldLen && newPos + 1 >= newLen) {
          return done(this.buildValues(basePath.lastComponent, newTokens, oldTokens)) || true;
        } else {
          bestPath[diagonalPath] = basePath;
          if (basePath.oldPos + 1 >= oldLen) {
            maxDiagonalToConsider = Math.min(maxDiagonalToConsider, diagonalPath - 1);
          }
          if (newPos + 1 >= newLen) {
            minDiagonalToConsider = Math.max(minDiagonalToConsider, diagonalPath + 1);
          }
        }
      }
      editLength++;
    };
    if (callback) {
      (function exec() {
        setTimeout(function() {
          if (editLength > maxEditLength || Date.now() > abortAfterTimestamp) {
            return callback(undefined);
          }
          if (!execEditLength()) {
            exec();
          }
        }, 0);
      })();
    } else {
      while (editLength <= maxEditLength && Date.now() <= abortAfterTimestamp) {
        const ret = execEditLength();
        if (ret) {
          return ret;
        }
      }
    }
  }
  addToPath(path, added, removed, oldPosInc, options) {
    const last = path.lastComponent;
    if (last && !options.oneChangePerToken && last.added === added && last.removed === removed) {
      return {
        oldPos: path.oldPos + oldPosInc,
        lastComponent: { count: last.count + 1, added, removed, previousComponent: last.previousComponent }
      };
    } else {
      return {
        oldPos: path.oldPos + oldPosInc,
        lastComponent: { count: 1, added, removed, previousComponent: last }
      };
    }
  }
  extractCommon(basePath, newTokens, oldTokens, diagonalPath, options) {
    const newLen = newTokens.length, oldLen = oldTokens.length;
    let oldPos = basePath.oldPos, newPos = oldPos - diagonalPath, commonCount = 0;
    while (newPos + 1 < newLen && oldPos + 1 < oldLen && this.equals(oldTokens[oldPos + 1], newTokens[newPos + 1], options)) {
      newPos++;
      oldPos++;
      commonCount++;
      if (options.oneChangePerToken) {
        basePath.lastComponent = { count: 1, previousComponent: basePath.lastComponent, added: false, removed: false };
      }
    }
    if (commonCount && !options.oneChangePerToken) {
      basePath.lastComponent = { count: commonCount, previousComponent: basePath.lastComponent, added: false, removed: false };
    }
    basePath.oldPos = oldPos;
    return newPos;
  }
  equals(left, right, options) {
    if (options.comparator) {
      return options.comparator(left, right);
    } else {
      return left === right || !!options.ignoreCase && left.toLowerCase() === right.toLowerCase();
    }
  }
  removeEmpty(array) {
    const ret = [];
    for (let i5 = 0;i5 < array.length; i5++) {
      if (array[i5]) {
        ret.push(array[i5]);
      }
    }
    return ret;
  }
  castInput(value, options) {
    return value;
  }
  tokenize(value, options) {
    return Array.from(value);
  }
  join(chars) {
    return chars.join("");
  }
  postProcess(changeObjects, options) {
    return changeObjects;
  }
  get useLongestToken() {
    return false;
  }
  buildValues(lastComponent, newTokens, oldTokens) {
    const components = [];
    let nextComponent;
    while (lastComponent) {
      components.push(lastComponent);
      nextComponent = lastComponent.previousComponent;
      delete lastComponent.previousComponent;
      lastComponent = nextComponent;
    }
    components.reverse();
    const componentLen = components.length;
    let componentPos = 0, newPos = 0, oldPos = 0;
    for (;componentPos < componentLen; componentPos++) {
      const component = components[componentPos];
      if (!component.removed) {
        if (!component.added && this.useLongestToken) {
          let value = newTokens.slice(newPos, newPos + component.count);
          value = value.map(function(value2, i5) {
            const oldValue = oldTokens[oldPos + i5];
            return oldValue.length > value2.length ? oldValue : value2;
          });
          component.value = this.join(value);
        } else {
          component.value = this.join(newTokens.slice(newPos, newPos + component.count));
        }
        newPos += component.count;
        if (!component.added) {
          oldPos += component.count;
        }
      } else {
        component.value = this.join(oldTokens.slice(oldPos, oldPos + component.count));
        oldPos += component.count;
      }
    }
    return components;
  }
}

// node_modules/diff/libesm/diff/line.js
class LineDiff extends Diff {
  constructor() {
    super(...arguments);
    this.tokenize = tokenize;
  }
  equals(left, right, options) {
    if (options.ignoreWhitespace) {
      if (!options.newlineIsToken || !left.includes(`
`)) {
        left = left.trim();
      }
      if (!options.newlineIsToken || !right.includes(`
`)) {
        right = right.trim();
      }
    } else if (options.ignoreNewlineAtEof && !options.newlineIsToken) {
      if (left.endsWith(`
`)) {
        left = left.slice(0, -1);
      }
      if (right.endsWith(`
`)) {
        right = right.slice(0, -1);
      }
    }
    return super.equals(left, right, options);
  }
}
var lineDiff = new LineDiff;
function diffLines(oldStr, newStr, options) {
  return lineDiff.diff(oldStr, newStr, options);
}
function tokenize(value, options) {
  if (options.stripTrailingCr) {
    value = value.replace(/\r\n/g, `
`);
  }
  const retLines = [], linesAndNewlines = value.split(/(\n|\r\n)/);
  if (!linesAndNewlines[linesAndNewlines.length - 1]) {
    linesAndNewlines.pop();
  }
  for (let i5 = 0;i5 < linesAndNewlines.length; i5++) {
    const line = linesAndNewlines[i5];
    if (i5 % 2 && !options.newlineIsToken) {
      retLines[retLines.length - 1] += line;
    } else {
      retLines.push(line);
    }
  }
  return retLines;
}
// custom_components/llm_gateway/frontend/voice-harness-replay-diff.ts
function object(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
function runId(record) {
  return String(record.run_id || record.id || "");
}
function resolveReplayPair(records, selected) {
  const forks = records.filter((record) => object(record.lineage).mode === "dry_run");
  const fork = selected?.forkId ? forks.find((record) => runId(record) === selected.forkId) : forks[0];
  if (!fork)
    return null;
  const lineage = object(fork.lineage);
  const sourceId = String(selected?.sourceId || lineage.replay_of || "");
  const source = records.find((record) => runId(record) === sourceId);
  if (!source)
    return null;
  return { source, fork, sourceId, forkId: runId(fork) };
}
function stable(value) {
  if (Array.isArray(value)) {
    return `[
${value.map((item) => `  ${stable(item)}`).join(`,
`)}
]`;
  }
  if (value && typeof value === "object") {
    const record = value;
    return `{
${Object.keys(record).sort().map((key) => `  ${JSON.stringify(key)}: ${stable(record[key])}`).join(`,
`)}
}`;
  }
  return JSON.stringify(value ?? null);
}
function timeline(record) {
  const spans = record.timeline_spans;
  const events = Array.isArray(spans) && spans.length ? spans : record.timeline;
  return Array.isArray(events) ? events.map((item) => {
    const event = object(item);
    return {
      stage: event.stage,
      status: event.status,
      start_ms: event.start_ms ?? event.t_ms,
      duration_ms: event.duration_ms ?? 0
    };
  }) : [];
}
function actions(record) {
  if (Array.isArray(record.proposed_actions))
    return record.proposed_actions;
  const raw = object(record.raw_payload);
  return Array.isArray(raw.proposed_actions) ? raw.proposed_actions : [];
}
function speech(record) {
  const speechValue = object(record.speech);
  return String(speechValue.final || record.final_speech_text || record.assistant_text || "");
}
function replayDiffSections(source, fork) {
  const values = [
    ["route", object(source.route), object(fork.route)],
    ["actions", actions(source), actions(fork)],
    ["speech", speech(source), speech(fork)],
    ["events", timeline(source), timeline(fork)]
  ];
  return values.map(([id, before, after]) => {
    const left = typeof before === "string" ? before : stable(before);
    const right = typeof after === "string" ? after : stable(after);
    return {
      id,
      changed: left !== right,
      parts: diffLines(`${left}
`, `${right}
`)
    };
  });
}

// custom_components/llm_gateway/frontend/voice-harness-replay-inspector.ts
class VoiceHarnessReplayInspector extends i4 {
  static properties = {
    pair: { attribute: false },
    labels: { attribute: false }
  };
  constructor() {
    super();
    this.pair = null;
    this.labels = {};
  }
  render() {
    if (!this.pair)
      return A;
    const sections = replayDiffSections(this.pair.source, this.pair.fork);
    const changed = sections.filter((section) => section.changed).length;
    return b2`
      <section>
        <header>
          <div><span class="eyebrow">Replay / Fork</span><strong>Diff Inspector</strong></div>
          <span class=${changed ? "chip warning" : "chip ok"}>${changed} changed</span>
        </header>
        <div class="lineage">
          <span>${this.pair.sourceId}</span><b aria-hidden="true">→</b><span>${this.pair.forkId}</span>
        </div>
        <div class="sections">
          ${sections.map((item) => b2`
            <details class="diff" ?open=${item.changed}>
              <summary>
                <strong>${this.labels[item.id] || item.id}</strong>
                <span class=${item.changed ? "chip warning" : "chip muted"}>
                  ${item.changed ? "changed" : "unchanged"}
                </span>
              </summary>
              <pre>${item.parts.map((part) => b2`<span class=${part.added ? "added" : part.removed ? "removed" : "same"}>${part.value}</span>`)}</pre>
            </details>
          `)}
        </div>
      </section>
    `;
  }
  static styles = i`
    :host { display: block; margin: 14px 0; color: var(--primary-text-color); }
    section { overflow: hidden; border: 1px solid var(--divider-color); border-radius: 8px; background: var(--card-background-color); }
    header { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 48px; padding: 0 12px; border-bottom: 1px solid var(--divider-color); }
    header > div { display: grid; gap: 2px; }
    .eyebrow { color: var(--secondary-text-color); font-size: 10px; font-weight: 650; letter-spacing: .04em; text-transform: uppercase; }
    .chip { display: inline-flex; align-items: center; min-height: 20px; padding: 0 7px; border-radius: 999px; font-size: 10px; font-weight: 650; }
    .warning { background: color-mix(in srgb, var(--warning-color, #f9a825) 16%, transparent); color: var(--warning-color, #a66a00); }
    .ok { background: color-mix(in srgb, var(--success-color, #43a047) 15%, transparent); color: var(--success-color, #2e7d32); }
    .muted { background: color-mix(in srgb, var(--secondary-text-color) 11%, transparent); color: var(--secondary-text-color); }
    .lineage { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid var(--divider-color); color: var(--secondary-text-color); font-family: var(--code-font-family, Menlo, Consolas, monospace); font-size: 10px; }
    .lineage span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .lineage b { color: var(--primary-color); }
    .sections { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .diff { min-width: 0; border-right: 1px solid var(--divider-color); border-bottom: 1px solid var(--divider-color); }
    .diff:nth-child(2n) { border-right: 0; }
    summary { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 38px; padding: 0 10px; cursor: pointer; font-size: 11px; }
    pre { max-height: 220px; margin: 0; padding: 8px 10px; overflow: auto; border-top: 1px solid var(--divider-color); background: var(--primary-background-color); font: 10px/1.5 var(--code-font-family, Menlo, Consolas, monospace); white-space: pre-wrap; }
    pre span { display: block; margin: 0 -10px; padding: 0 10px; }
    .added { background: color-mix(in srgb, var(--success-color, #43a047) 16%, transparent); color: var(--success-color, #2e7d32); }
    .removed { background: color-mix(in srgb, var(--error-color) 13%, transparent); color: var(--error-color); text-decoration: line-through; }
    @media (max-width: 560px) { .sections { grid-template-columns: 1fr; } .diff { border-right: 0; } }
  `;
}
if (!customElements.get("voice-harness-replay-inspector")) {
  customElements.define("voice-harness-replay-inspector", VoiceHarnessReplayInspector);
}

// custom_components/llm_gateway/frontend/voice-harness-run-list.ts
class VoiceHarnessRunList extends i4 {
  static properties = {
    items: { attribute: false },
    selected: { type: String }
  };
  constructor() {
    super();
    this.items = [];
    this.selected = "";
  }
  render() {
    return b2`
      <div role="listbox" aria-label="Voice Harness runs">
        ${this.items.map((item) => b2`
            <button
              aria-selected=${String(item.id === this.selected)}
              data-id=${item.id}
              role="option"
              tabindex=${item.id === this.selected ? "0" : "-1"}
              @click=${() => this.select(item.id)}
              @keydown=${this.onKeydown}
            >
              <span class="status ${item.status}" aria-hidden="true"></span>
              <span class="identity">
                <strong>${item.title}</strong>
                <small>${item.subtitle}</small>
              </span>
              <span class="facts"><small>${item.route}</small><small>${item.latency}</small></span>
            </button>
          `)}
      </div>
    `;
  }
  select(id) {
    this.dispatchEvent(new CustomEvent("harness-run-select", {
      bubbles: true,
      composed: true,
      detail: { id }
    }));
  }
  onKeydown(event) {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key))
      return;
    event.preventDefault();
    const current = this.items.findIndex((item2) => item2.id === this.selected);
    let next = current < 0 ? 0 : current;
    if (event.key === "Home")
      next = 0;
    if (event.key === "End")
      next = this.items.length - 1;
    if (event.key === "ArrowUp")
      next = (next - 1 + this.items.length) % this.items.length;
    if (event.key === "ArrowDown")
      next = (next + 1) % this.items.length;
    const item = this.items[next];
    if (!item)
      return;
    this.select(item.id);
    this.renderRoot.querySelector(`button[data-id="${CSS.escape(item.id)}"]`)?.focus();
  }
  static styles = [harnessFoundationStyles, harnessButtonStyles, i`
    :host { display: block; min-width: 0; }
    div { display: grid; gap: var(--vh-space-xs); }
    button { width: 100%; min-height: 64px; display: grid; grid-template-columns: 8px minmax(0, 1fr) auto; gap: var(--vh-space-s); align-items: center; padding: var(--vh-space-s); background: transparent; text-align: left; }
    button:hover { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
    button[aria-selected="true"] { background: color-mix(in srgb, var(--primary-color) 13%, var(--card-background-color)); }
    .status { width: 7px; height: 7px; border-radius: 50%; background: var(--secondary-text-color); }
    .status.ok { background: var(--success-color); }
    .status.warning { background: var(--warning-color); }
    .status.bad { background: var(--error-color); }
    .identity, .facts { min-width: 0; display: grid; gap: 3px; }
    strong, small { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    strong { font-size: 12px; }
    small { color: var(--secondary-text-color); font-size: 10px; }
    .facts { justify-items: end; }
  `];
}
if (!customElements.get("voice-harness-run-list")) {
  customElements.define("voice-harness-run-list", VoiceHarnessRunList);
}
export {
  resolveReplayPair
};
