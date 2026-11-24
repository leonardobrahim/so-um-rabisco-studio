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

function escolherTipoCamera(cena, index, ehGancho, ehHorizontal) {
    if (ehHorizontal) {
        const efeito = (cena.efeito || "").toLowerCase();
        if (efeito === "pop-in" || efeito === "impact-pop" || efeito === "shake") {
            return "impact-pop";
        }
        if (index > 0 && index % 5 === 0) {
            return index % 10 === 0 ? "slide-left" : "slide-transition";
        }
        const cicloLongo = [
            "zoom-in",
            "ken-burns-right",
            "zoom-out",
            "ken-burns-left",
            "zoom-in",
            "ken-burns-up",
        ];
        return cicloLongo[index % cicloLongo.length];
    }

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

function aplicarAnimacaoCena(tl, el, cena, index, ehHorizontal) {
    const inicio = Number(cena.inicio) || 0;
    const fim = Number(cena.fim) || inicio + 1.5;
    const duracao = Math.max(0.15, fim - inicio);
    const escalaBase = Number(cena.escala) || 1.0;
    const efeito = (cena.efeito || "pop-in").toLowerCase();
    const ehGancho = inicio < 10.0;
    const modoCamera = escolherTipoCamera(cena, index, ehGancho, ehHorizontal);

    // Em 16:9 full-bleed, alterna o ponto de foco e mantém overscan >= 1.07 para nunca revelar bordas
    const focos = ["50% 45%", "38% 45%", "62% 45%", "50% 38%"];
    const origemFoco = ehHorizontal ? focos[index % focos.length] : "center center";

    tl.set(
        el,
        {
            autoAlpha: 1,
            scale: ehHorizontal ? escalaBase * 1.07 : escalaBase,
            x: 0,
            y: 0,
            xPercent: 0,
            yPercent: 0,
            rotation: 0,
            transformOrigin: origemFoco,
        },
        inicio
    );

    if (ehHorizontal) {
        const tilt = index % 2 === 0 ? 0.45 : -0.45;
        if (modoCamera === "ken-burns-right") {
            tl.fromTo(
                el,
                { scale: escalaBase * 1.11, xPercent: -2.5, yPercent: 0.6, rotation: 0 },
                { scale: escalaBase * 1.15, xPercent: 2.5, yPercent: -0.6, rotation: tilt, duration: duracao, ease: "none" },
                inicio
            );
        } else if (modoCamera === "ken-burns-left") {
            tl.fromTo(
                el,
                { scale: escalaBase * 1.11, xPercent: 2.5, yPercent: -0.6, rotation: 0 },
                { scale: escalaBase * 1.15, xPercent: -2.5, yPercent: 0.6, rotation: -tilt, duration: duracao, ease: "none" },
                inicio
            );
        } else if (modoCamera === "ken-burns-up") {
            tl.fromTo(
                el,
                { scale: escalaBase * 1.10, yPercent: 2.2, xPercent: 0 },
                { scale: escalaBase * 1.15, yPercent: -2.2, xPercent: index % 2 === 0 ? 1.0 : -1.0, duration: duracao, ease: "none" },
                inicio
            );
        } else if (modoCamera === "slide-transition") {
            const durTrans = Math.min(0.22, duracao * 0.3);
            tl.fromTo(
                el,
                { yPercent: 100, scale: escalaBase * 1.08 },
                { yPercent: 0, scale: escalaBase * 1.09, duration: durTrans, ease: "power3.out" },
                inicio
            );
            if (duracao > durTrans) {
                tl.to(
                    el,
                    { scale: escalaBase * 1.15, xPercent: index % 2 === 0 ? 1.5 : -1.5, duration: duracao - durTrans, ease: "none" },
                    inicio + durTrans
                );
            }
        } else if (modoCamera === "slide-left") {
            const durTrans = Math.min(0.22, duracao * 0.3);
            tl.fromTo(
                el,
                { xPercent: 100, scale: escalaBase * 1.08 },
                { xPercent: 0, scale: escalaBase * 1.09, duration: durTrans, ease: "power3.out" },
                inicio
            );
            if (duracao > durTrans) {
                tl.to(
                    el,
                    { scale: escalaBase * 1.15, yPercent: -1.2, duration: duracao - durTrans, ease: "none" },
                    inicio + durTrans
                );
            }
        } else if (modoCamera === "impact-pop") {
            const durPop = Math.min(0.18, duracao * 0.3);
            tl.fromTo(
                el,
                { scale: escalaBase * 1.22, rotation: -tilt },
                { scale: escalaBase * 1.09, rotation: 0, duration: durPop, ease: "back.out(1.6)" },
                inicio
            );
            if (duracao > durPop) {
                tl.to(
                    el,
                    { scale: escalaBase * 1.14, xPercent: index % 2 === 0 ? 1.4 : -1.4, duration: duracao - durPop, ease: "none" },
                    inicio + durPop
                );
            }
        } else if (modoCamera === "zoom-out") {
            tl.fromTo(
                el,
                { scale: escalaBase * 1.18, xPercent: -1.2, rotation: tilt * 0.7 },
                { scale: escalaBase * 1.06, xPercent: 1.2, rotation: 0, duration: duracao, ease: "power1.out" },
                inicio
            );
        } else {
            // zoom-in focado no ponto de interesse
            tl.fromTo(
                el,
                { scale: escalaBase * 1.06, xPercent: 0, yPercent: 0, rotation: 0 },
                { scale: escalaBase * 1.17, xPercent: index % 2 === 0 ? 1.2 : -1.2, yPercent: -0.8, rotation: tilt * 0.7, duration: duracao, ease: "none" },
                inicio
            );
        }

        if (efeito === "shake") {
            const passos = [
                { x: -12, rotation: -0.8 },
                { x: 12, rotation: 0.8 },
                { x: -8, rotation: -0.5 },
                { x: 8, rotation: 0.5 },
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
        return;
    }

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

// ---------------------------------------------------------------- Camada do personagem
const ALTURA_PERSONAGEM = { horizontal: 0.52, vertical: 0.34 };

function criarCamadaPersonagem(p, ehHorizontal) {
    const compW = ehHorizontal ? 1920 : 1080;
    const compH = ehHorizontal ? 1080 : 1920;
    const escala = Number(p.escala) > 0 ? Number(p.escala) : 1;
    const lado = Math.round(compH * (ehHorizontal ? ALTURA_PERSONAGEM.horizontal : ALTURA_PERSONAGEM.vertical) * escala);
    const margem = Math.round(compW * 0.03);
    const posicao = p.posicao || "center";

    let left;
    if (posicao === "left" || posicao === "bottom-left") {
        left = margem;
    } else if (posicao === "right" || posicao === "bottom-corner") {
        left = compW - lado - margem;
    } else {
        left = Math.round((compW - lado) / 2);
    }

    const box = document.createElement("div");
    box.className = `cena-personagem pos-${posicao}`;
    box.style.width = `${lado}px`;
    box.style.height = `${lado}px`;
    box.style.left = `${left}px`;
    // Os quadros 512x512 deixam ~6% de margem na base: sobe/desce para os pés ficarem rente ao fim do quadro
    box.style.bottom = `${-Math.round(lado * 0.04)}px`;

    const inner = document.createElement("div");
    inner.className = p.flip ? "personagem-inner flip" : "personagem-inner";

    let sprite = null;
    let pronto = Promise.resolve();
    if (p.tipo === "sprite") {
        const cfg = p.sprite || {};
        const frames = Math.max(1, Number(cfg.frames) || 1);
        const el = document.createElement("div");
        el.className = "personagem-sprite";
        el.style.backgroundImage = `url("${p.arquivo}")`;
        el.style.backgroundSize = `${frames * lado}px ${lado}px`;
        inner.appendChild(el);
        sprite = { el, frames, fps: Math.max(1, Number(cfg.fps) || 8), lado };

        const pre = new Image();
        pre.src = p.arquivo;
        if (pre.decode) pronto = pre.decode().catch(() => { });
    } else {
        const img = document.createElement("img");
        img.src = p.arquivo;
        img.alt = "Personagem";
        inner.appendChild(img);
        if (img.decode) pronto = img.decode().catch(() => { });
    }

    box.appendChild(inner);
    return { box, sprite, pronto };
}

// O render do HyperFrames faz seek na timeline: nada de repeat infinito, o loop é finito pela duração da cena
function repeticoesFinitas(duracao, ciclo) {
    return Math.max(0, Math.ceil(duracao / ciclo) - 1);
}

function aplicarAnimacaoPersonagem(tl, camada, p, cena) {
    const box = camada.box;
    const inicio = Number(cena.inicio) || 0;
    const fim = Number(cena.fim) || inicio + 1.5;
    const duracao = Math.max(0.15, fim - inicio);
    const entrada = Math.min(0.35, duracao * 0.4);
    const animacao = String(p.animacao || "pop-in").toLowerCase();

    tl.set(box, { autoAlpha: 1, x: 0, y: 0, xPercent: 0, yPercent: 0, scale: 1, rotation: 0 }, inicio);

    // Sprite sheet (strip.png): quadros em loop com steps(), independente da animação de entrada
    // Usa sub-timeline + tweenFromTo para cortar exatamente no fim da cena sem alongar a timeline principal.
    if (camada.sprite) {
        const { el, frames, fps, lado } = camada.sprite;
        const ciclo = frames / fps;
        const spriteTl = gsap.timeline({ paused: true });
        spriteTl.fromTo(
            el,
            { backgroundPositionX: "0px" },
            {
                backgroundPositionX: `${-frames * lado}px`,
                duration: ciclo,
                ease: `steps(${frames})`,
                repeat: repeticoesFinitas(duracao, ciclo),
            },
            0
        );
        tl.add(spriteTl.tweenFromTo(0, duracao, { ease: "none" }), inicio);
    }

    if (animacao === "pop-in") {
        tl.fromTo(box, { scale: 0.2, opacity: 0 }, { scale: 1, opacity: 1, duration: entrada, ease: "back.out(1.8)" }, inicio);
    } else if (animacao === "slide-in-left") {
        tl.fromTo(box, { xPercent: -130 }, { xPercent: 0, duration: entrada, ease: "power3.out" }, inicio);
    } else if (animacao === "slide-in-right") {
        tl.fromTo(box, { xPercent: 130 }, { xPercent: 0, duration: entrada, ease: "power3.out" }, inicio);
    } else if (animacao === "bounce") {
        tl.fromTo(
            box,
            { yPercent: 45, opacity: 0 },
            { yPercent: 0, opacity: 1, duration: Math.min(0.5, duracao * 0.6), ease: "bounce.out" },
            inicio
        );
    } else if (animacao === "float") {
        tl.fromTo(box, { opacity: 0, yPercent: 6 }, { opacity: 1, yPercent: 0, duration: entrada, ease: "power2.out" }, inicio);
        const resto = duracao - entrada;
        if (resto > 0.3) {
            const meioCiclo = 0.55;
            const repeticoes = Math.max(1, Math.round(resto / meioCiclo)) - 1;
            tl.to(box, { yPercent: -3, duration: meioCiclo, ease: "sine.inOut", repeat: repeticoes, yoyo: true }, inicio + entrada);
        }
    } else if (animacao === "shake") {
        tl.fromTo(box, { scale: 0.3, opacity: 0 }, { scale: 1, opacity: 1, duration: entrada, ease: "back.out(1.8)" }, inicio);
        const passos = [
            { x: -14, rotation: -2 },
            { x: 14, rotation: 2 },
            { x: -9, rotation: -1.2 },
            { x: 9, rotation: 1.2 },
            { x: 0, rotation: 0 },
        ];
        const tempoPasso = Math.min(0.05, Math.max(0.02, (duracao - entrada) / (passos.length * 2)));
        passos.forEach((s, idx) => {
            tl.to(box, { x: s.x, rotation: s.rotation, duration: tempoPasso, ease: "none" }, inicio + entrada + idx * tempoPasso);
        });
    }
    // "none": o personagem só aparece (e o sprite, se houver, anima os quadros)

    tl.set(box, { autoAlpha: 0 }, fim);
}

async function inicializarComposicao() {
    const resposta = await fetch("./cenas.json");
    const dados = await resposta.json();

    const formato = dados.formato || "9:16";
    const ehHorizontal = formato === "16:9";
    configurarDimensoes(formato);

    const comp = document.getElementById("composition");
    if (dados.fps) {
        comp.setAttribute("data-fps", String(dados.fps));
    }
    if (dados.duracao_total) {
        comp.setAttribute("data-duration", String(dados.duracao_total));
    }

    const stage = document.getElementById("stage");
    const captionLayer = document.getElementById("caption-layer");
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
        img.src = (cena.fundo && cena.fundo.arquivo) || cena.arquivo;
        img.alt = `Cena ${index + 1}`;
        if (img.decode) {
            imagensParaCarregar.push(img.decode().catch(() => { }));
        }

        // Cenas antigas (sem "personagem") ou com tipo "none" renderizam só a imagem fechada, como sempre
        const personagem = cena.personagem;
        const temPersonagem =
            personagem && (personagem.tipo === "pose" || personagem.tipo === "sprite") && personagem.arquivo;

        if (temPersonagem) {
            // Cena em camadas: a câmera (zoom/ken-burns) age só no fundo; o personagem tem animação própria
            const inicioCena = Number(cena.inicio) || 0;
            const fimCena = Number(cena.fim) || inicioCena + 1.5;
            const fundo = document.createElement("div");
            fundo.className = "cena-fundo";
            fundo.appendChild(img);
            wrapper.appendChild(fundo);

            const camada = criarCamadaPersonagem(personagem, ehHorizontal);
            wrapper.appendChild(camada.box);
            stage.appendChild(wrapper);
            imagensParaCarregar.push(camada.pronto);

            aplicarAnimacaoCena(mainTimeline, fundo, cena, index, ehHorizontal);
            mainTimeline.set(wrapper, { autoAlpha: 1 }, inicioCena);
            mainTimeline.set(wrapper, { autoAlpha: 0 }, fimCena);
            aplicarAnimacaoPersonagem(mainTimeline, camada, personagem, cena);
        } else {
            wrapper.appendChild(img);
            stage.appendChild(wrapper);
            aplicarAnimacaoCena(mainTimeline, wrapper, cena, index, ehHorizontal);
        }
        if (mostrarLegendas) {
            aplicarLegendas(mainTimeline, captionLayer, cena);
        }
    });

    if (dados.duracao_total) {
        const durTotal = Number(dados.duracao_total);
        mainTimeline.to({}, { duration: 0.01 }, durTotal);
    }

    await Promise.all(imagensParaCarregar);
    window.__HYPERFRAMES_READY__ = true;
}

inicializarComposicao();
