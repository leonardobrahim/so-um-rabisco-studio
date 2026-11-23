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

function escolherTipoCamera(cena, index) {
    // A cada 4 ou 5 cenas, aplica slide-transition rápida de mudança de bloco narrativo
    if (index > 0 && index % 4 === 0) {
        return "slide-transition";
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
    const fim = Number(cena.fim) || inicio + 1.8;
    const duracao = Math.max(0.15, fim - inicio);
    const escalaBase = Number(cena.escala) || 1.0;
    const efeito = (cena.efeito || "pop-in").toLowerCase();
    const modoCamera = escolherTipoCamera(cena, index);

    // Ativa visibilidade exatamente no frame de entrada
    tl.set(
        el,
        {
            autoAlpha: 1,
            scale: escalaBase,
            x: 0,
            y: 0,
            yPercent: 0,
            rotation: 0,
        },
        inicio
    );

    if (modoCamera === "slide-transition") {
        // Transição rápida de bloco narrativo (0.22s de baixo para cima) + zoom-in contínuo
        tl.fromTo(
            el,
            { yPercent: 100, scale: escalaBase },
            { yPercent: 0, scale: escalaBase * 1.03, duration: Math.min(0.22, duracao * 0.4), ease: "power3.out" },
            inicio
        );
        if (duracao > 0.25) {
            tl.to(
                el,
                { scale: escalaBase * 1.09, duration: duracao - 0.22, ease: "none" },
                inicio + 0.22
            );
        }
    } else if (modoCamera === "impact-pop") {
        // Entrada rápida de impacto (0.18s) de 1.14 para 1.02 com back.out(1.7)
        const durPop = Math.min(0.18, duracao * 0.4);
        tl.fromTo(
            el,
            { scale: escalaBase * 1.14 },
            { scale: escalaBase * 1.02, duration: durPop, ease: "back.out(1.7)" },
            inicio
        );
        if (duracao > durPop) {
            tl.to(
                el,
                { scale: escalaBase * 1.07, duration: duracao - durPop, ease: "none" },
                inicio + durPop
            );
        }
    } else if (modoCamera === "zoom-out") {
        // Recuo suave de 1.09 para 1.0
        tl.fromTo(
            el,
            { scale: escalaBase * 1.09 },
            { scale: escalaBase, duration: duracao, ease: "power1.out" },
            inicio
        );
    } else {
        // zoom-in contínuo suave de 1.0 até 1.09
        tl.fromTo(
            el,
            { scale: escalaBase },
            { scale: escalaBase * 1.09, duration: duracao, ease: "none" },
            inicio
        );
    }

    if (efeito === "shake") {
        const passos = [
            { x: -12, rotation: -1.2 },
            { x: 12, rotation: 1.2 },
            { x: -8, rotation: -0.8 },
            { x: 8, rotation: 0.8 },
            { x: 0, rotation: 0 },
        ];
        const tempoPasso = Math.min(0.05, duracao / (passos.length * 2));
        passos.forEach((p, idx) => {
            tl.to(
                el,
                { x: p.x, rotation: p.rotation, duration: tempoPasso, ease: "none" },
                inicio + idx * tempoPasso
            );
        });
    }

    // Saída limpa para a próxima cena assumir
    tl.set(el, { autoAlpha: 0 }, fim);
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
    const fimCena = Number(cena.fim) || inicioCena + 1.8;

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

        // Pop rápido de retenção: scale 0.75 -> 1.05 -> 1.0 em 0.15s
        tl.fromTo(
            el,
            { autoAlpha: 0, scale: 0.75, xPercent: -50 },
            { autoAlpha: 1, scale: 1.05, xPercent: -50, duration: 0.09, ease: "power2.out" },
            bIni
        );
        tl.to(
            el,
            { scale: 1.0, xPercent: -50, duration: 0.06, ease: "power1.out" },
            bIni + 0.09
        );

        // Desaparece exatamente quando o próximo bloco entra
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
    const captionLayer = document.getElementById("caption-layer");
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
        aplicarLegendas(mainTimeline, captionLayer, cena);
    });

    if (dados.duracao_total) {
        mainTimeline.to({}, { duration: 0.01 }, Number(dados.duracao_total));
    }

    await Promise.all(imagensParaCarregar);
    window.__HYPERFRAMES_READY__ = true;
}

inicializarComposicao();
