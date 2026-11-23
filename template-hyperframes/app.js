window.__timelines = window.__timelines || {};

const mainTimeline = gsap.timeline({ paused: true });
window.__timelines["main"] = mainTimeline;

function configurarDimensoes(formato) {
    const comp = document.getElementById("composition");
    if (formato === "16:9") {
        comp.classList.add("formato-horizontal");
        comp.setAttribute("data-width", "1920");
        comp.setAttribute("data-height", "1080");
    } else {
        comp.classList.remove("formato-horizontal");
        comp.setAttribute("data-width", "1080");
        comp.setAttribute("data-height", "1920");
    }
}

function escolherTipoCamera(cena, index, ehGancho) {
    // Nos primeiros 10s (gancho), prioriza entradas de impacto e transições rápidas
    if (ehGancho) {
        const cicloGancho = ["impact-pop", "slide-transition", "impact-pop", "slide-left", "zoom-in"];
        return cicloGancho[index % cicloGancho.length];
    }

    if (index > 0 && index % 4 === 0) {
        return index % 8 === 0 ? "slide-left" : "slide-transition";
    }

    const efeito = (cena.efeito || "").toLowerCase();
    if (efeito === "pop-in" || efeito === "impact-pop" || efeito === "shake") {
        return "impact-pop";
    }
    if (efeito === "zoom-in") return "zoom-in";
    if (efeito === "zoom-out") return "zoom-out";

    return index % 2 === 0 ? "zoom-in" : "zoom-out";
}

function aplicarAnimacaoCena(tl, el, cena, index) {
    const inicio = Number(cena.inicio) || 0;
    const fim = Number(cena.fim) || inicio + 1.5;
    const duracao = Math.max(0.15, fim - inicio);
    const escalaBase = Number(cena.escala) || 1.0;
    const efeito = (cena.efeito || "pop-in").toLowerCase();
    const ehGancho = inicio < 10.0;
    const modoCamera = escolherTipoCamera(cena, index, ehGancho);

    tl.set(
        el,
        {
            autoAlpha: 1,
            scale: escalaBase,
            x: 0,
            y: 0,
            xPercent: 0,
            yPercent: 0,
            rotation: 0,
        },
        inicio
    );

    const driftX = index % 2 === 0 ? 16 : -16;
    const tilt = index % 2 === 0 ? 1.1 : -1.1;

    if (modoCamera === "slide-transition") {
        const durTrans = Math.min(0.18, duracao * 0.35);
        tl.fromTo(
            el,
            { yPercent: 100, scale: escalaBase * 1.02 },
            { yPercent: 0, scale: escalaBase * 1.04, duration: durTrans, ease: "power3.out" },
            inicio
        );
        if (duracao > durTrans) {
            tl.to(
                el,
                { scale: escalaBase * 1.11, x: driftX, rotation: tilt, duration: duracao - durTrans, ease: "none" },
                inicio + durTrans
            );
        }
    } else if (modoCamera === "slide-left") {
        const durTrans = Math.min(0.18, duracao * 0.35);
        tl.fromTo(
            el,
            { xPercent: 100, scale: escalaBase * 1.02 },
            { xPercent: 0, scale: escalaBase * 1.04, duration: durTrans, ease: "power3.out" },
            inicio
        );
        if (duracao > durTrans) {
            tl.to(
                el,
                { scale: escalaBase * 1.11, y: -12, rotation: -tilt, duration: duracao - durTrans, ease: "none" },
                inicio + durTrans
            );
        }
    } else if (modoCamera === "impact-pop") {
        const durPop = Math.min(0.16, duracao * 0.35);
        tl.fromTo(
            el,
            { scale: escalaBase * (ehGancho ? 1.18 : 1.14), rotation: -tilt },
            { scale: escalaBase * 1.02, rotation: 0, duration: durPop, ease: "back.out(1.7)" },
            inicio
        );
        if (duracao > durPop) {
            tl.to(
                el,
                { scale: escalaBase * 1.10, x: driftX * 0.7, duration: duracao - durPop, ease: "none" },
                inicio + durPop
            );
        }
    } else if (modoCamera === "zoom-out") {
        tl.fromTo(
            el,
            { scale: escalaBase * 1.12, x: -driftX, rotation: tilt * 0.8 },
            { scale: escalaBase * 1.0, x: driftX * 0.5, rotation: 0, duration: duracao, ease: "power1.out" },
            inicio
        );
    } else {
        tl.fromTo(
            el,
            { scale: escalaBase, x: 0, rotation: 0 },
            { scale: escalaBase * 1.11, x: driftX, rotation: tilt, duration: duracao, ease: "none" },
            inicio
        );
    }

    if (efeito === "shake") {
        const passos = [
            { x: -14, rotation: -1.5 },
            { x: 14, rotation: 1.5 },
            { x: -10, rotation: -1.0 },
            { x: 10, rotation: 1.0 },
            { x: 0, rotation: 0 },
        ];
        const tempoPasso = Math.min(0.045, duracao / (passos.length * 2));
        passos.forEach((p, idx) => {
            tl.to(
                el,
                { x: p.x, rotation: p.rotation, duration: tempoPasso, ease: "none" },
                inicio + idx * tempoPasso
            );
        });
    }

    tl.set(el, { autoAlpha: 0 }, fim);
}

function aplicarDoodleBurst(tl, fxLayer, cena, index) {
    const inicio = Number(cena.inicio) || 0;
    const fim = Number(cena.fim) || inicio + 1.5;
    const ehGancho = inicio < 10.0;
    const efeito = (cena.efeito || "").toLowerCase();

    // Adiciona risquinhos de ênfase estilo rabisco 2D no gancho e em momentos de impacto
    if (!ehGancho && efeito !== "shake" && index % 3 !== 0) return;

    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("class", "doodle-burst");
    svg.setAttribute("viewBox", "0 0 100 100");
    svg.setAttribute("preserveAspectRatio", "none");

    const linhas = [
        { x1: "10", y1: "16", x2: "16", y2: "20", cor: "#111111" },
        { x1: "8", y1: "22", x2: "14", y2: "24", cor: "#FFC928" },
        { x1: "90", y1: "16", x2: "84", y2: "20", cor: "#111111" },
        { x1: "92", y1: "22", x2: "86", y2: "24", cor: "#FFC928" },
    ];
    linhas.forEach((l) => {
        const line = document.createElementNS(svgNS, "line");
        line.setAttribute("x1", l.x1);
        line.setAttribute("y1", l.y1);
        line.setAttribute("x2", l.x2);
        line.setAttribute("y2", l.y2);
        line.setAttribute("stroke", l.cor);
        line.setAttribute("stroke-width", "0.7");
        line.setAttribute("stroke-linecap", "round");
        svg.appendChild(line);
    });

    fxLayer.appendChild(svg);

    tl.fromTo(
        svg,
        { autoAlpha: 0, scale: 0.85 },
        { autoAlpha: 0.9, scale: 1.05, duration: 0.14, ease: "back.out(2)" },
        inicio
    );
    tl.to(svg, { autoAlpha: 0, duration: 0.25 }, Math.min(fim, inicio + 0.45));
}

function dividirFalaCurtaFallback(fala, inicio, fim) {
    const palavras = String(fala || "").trim().split(/\s+/).filter(Boolean);
    if (!palavras.length) return [];

    const dur = Math.max(0.25, fim - inicio);
    const maxP = dur >= 1.2 ? 3 : 2;
    const grupos = [];
    for (let i = 0; i < palavras.length; i += maxP) {
        grupos.push(palavras.slice(i, i + maxP));
    }

    let cursor = inicio;
    return grupos.map((g, idx) => {
        const bFim = idx === grupos.length - 1 ? fim : cursor + dur * (g.length / palavras.length);
        const cor = idx % 3 === 1 ? "canal" : "branco";
        const item = { texto: g.join(" "), inicio: cursor, fim: Math.max(cursor + 0.2, bFim), cor };
        cursor = bFim;
        return item;
    });
}

function aplicarLegendas(tl, layer, cena) {
    const inicioCena = Number(cena.inicio) || 0;
    const fimCena = Number(cena.fim) || inicioCena + 1.5;

    let blocos = Array.isArray(cena.legendas) && cena.legendas.length > 0 ? cena.legendas : null;
    if (!blocos) {
        const falaFallback = (cena.narracao || cena.texto || "").trim();
        if (!falaFallback) return;
        blocos = dividirFalaCurtaFallback(falaFallback, inicioCena, fimCena);
    }

    blocos.forEach((bloco, idx) => {
        const texto = String(bloco.texto || "").trim();
        if (!texto) return;

        const bIni = Number(bloco.inicio) ?? inicioCena;
        const bFim = Number(bloco.fim) ?? fimCena;
        const cor = bloco.cor || (idx % 3 === 1 ? "canal" : "branco");

        const el = document.createElement("div");
        el.className = `legenda-bloco legenda-${cor}`;
        el.textContent = texto;
        layer.appendChild(el);

        // Sem xPercent/translateX para manter centralização matemática perfeita via width: 100% + text-align: center
        tl.fromTo(
            el,
            { autoAlpha: 0, scale: 0.75 },
            { autoAlpha: 1, scale: 1.05, duration: 0.09, ease: "power2.out" },
            bIni
        );
        tl.to(
            el,
            { scale: 1.0, duration: 0.06, ease: "power1.out" },
            bIni + 0.09
        );

        tl.set(el, { autoAlpha: 0 }, bFim);
    });
}

async function inicializarComposicao() {
    const resposta = await fetch("./cenas.json");
    const dados = await resposta.json();

    configurarDimensoes(dados.formato || "9:16");

    const comp = document.getElementById("composition");
    if (dados.fps) {
        comp.setAttribute("data-fps", String(dados.fps));
    }
    if (dados.duracao_total) {
        comp.setAttribute("data-duration", String(dados.duracao_total));
    }

    const stage = document.getElementById("stage");
    const fxLayer = document.getElementById("fx-layer");
    const captionLayer = document.getElementById("caption-layer");
    const progressBar = document.getElementById("progress-bar");
    const mostrarLegendas = dados.mostrar_legendas !== false;
    if (captionLayer && !mostrarLegendas) {
        captionLayer.style.display = "none";
    }
    const imagensParaCarregar = [];

    (dados.cenas || []).forEach((cena, index) => {
        const wrapper = document.createElement("div");
        wrapper.className = "cena-item";
        wrapper.id = `cena-${index + 1}`;

        const img = document.createElement("img");
        img.src = cena.arquivo;
        img.alt = `Cena ${index + 1}`;
        wrapper.appendChild(img);
        stage.appendChild(wrapper);

        if (img.decode) {
            imagensParaCarregar.push(img.decode().catch(() => { }));
        }

        aplicarAnimacaoCena(mainTimeline, wrapper, cena, index);
        aplicarDoodleBurst(mainTimeline, fxLayer, cena, index);
        if (mostrarLegendas) {
            aplicarLegendas(mainTimeline, captionLayer, cena);
        }
    });

    if (dados.duracao_total) {
        const durTotal = Number(dados.duracao_total);
        if (progressBar) {
            mainTimeline.fromTo(
                progressBar,
                { scaleX: 0 },
                { scaleX: 1, duration: durTotal, ease: "none" },
                0
            );
        }
        mainTimeline.to({}, { duration: 0.01 }, durTotal);
    }

    await Promise.all(imagensParaCarregar);
    window.__HYPERFRAMES_READY__ = true;
}

inicializarComposicao();
