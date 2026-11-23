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

function aplicarAnimacaoCena(tl, el, cena) {
    const inicio = Number(cena.inicio) || 0;
    const fim = Number(cena.fim) || inicio + 1.5;
    const duracao = Math.max(0.1, fim - inicio);
    const escalaBase = Number(cena.escala) || 1.0;
    const efeito = (cena.efeito || "cut").toLowerCase();

    // Ativa visibilidade exatamente no frame de entrada
    tl.set(
        el,
        {
            autoAlpha: 1,
            scale: escalaBase,
            x: 0,
            y: 0,
            rotation: 0,
        },
        inicio
    );

    if (efeito === "pop-in") {
        tl.fromTo(
            el,
            { scale: escalaBase * 0.86 },
            {
                scale: escalaBase,
                duration: Math.min(0.22, duracao * 0.4),
                ease: "back.out(2.2)",
            },
            inicio
        );
    } else if (efeito === "zoom-in") {
        tl.fromTo(
            el,
            { scale: escalaBase },
            {
                scale: escalaBase * 1.12,
                duration: duracao,
                ease: "none",
            },
            inicio
        );
    } else if (efeito === "zoom-out") {
        tl.fromTo(
            el,
            { scale: escalaBase * 1.14 },
            {
                scale: escalaBase,
                duration: duracao,
                ease: "power1.out",
            },
            inicio
        );
    } else if (efeito === "slide-up") {
        tl.fromTo(
            el,
            { y: 180, autoAlpha: 0 },
            {
                y: 0,
                autoAlpha: 1,
                duration: Math.min(0.25, duracao * 0.45),
                ease: "power3.out",
            },
            inicio
        );
    } else if (efeito === "shake") {
        // Keyframes fixos garantem determinismo frame a frame no renderizador
        const passos = [
            { x: -16, rotation: -1.5 },
            { x: 16, rotation: 1.5 },
            { x: -12, rotation: -1.0 },
            { x: 12, rotation: 1.0 },
            { x: -6, rotation: -0.5 },
            { x: 0, rotation: 0 },
        ];
        const tempoPasso = Math.min(0.06, duracao / (passos.length * 2));
        passos.forEach((p, idx) => {
            tl.to(
                el,
                {
                    x: p.x,
                    rotation: p.rotation,
                    duration: tempoPasso,
                    ease: "none",
                },
                inicio + idx * tempoPasso
            );
        });
    }

    // Corte seco na saída para a próxima cena assumir limpa
    tl.set(el, { autoAlpha: 0 }, fim);
}

function aplicarTextoDestaque(tl, layer, cena) {
    if (!cena.texto || !cena.texto.trim()) return;

    const inicio = Number(cena.inicio) || 0;
    const fim = Number(cena.fim) || inicio + 1.5;
    const duracao = Math.max(0.1, fim - inicio);

    const badge = document.createElement("div");
    badge.className = "texto-impacto";
    badge.textContent = cena.texto.trim();
    layer.appendChild(badge);

    tl.fromTo(
        badge,
        { autoAlpha: 0, scale: 0.85, y: 20 },
        {
            autoAlpha: 1,
            scale: 1,
            y: 0,
            duration: Math.min(0.18, duracao * 0.3),
            ease: "back.out(1.8)",
        },
        inicio
    );

    tl.set(badge, { autoAlpha: 0 }, fim);
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

        aplicarAnimacaoCena(mainTimeline, wrapper, cena);
        aplicarTextoDestaque(mainTimeline, captionLayer, cena);
    });

    // Garante que a timeline tenha exatamente a duração total do áudio
    if (dados.duracao_total) {
        mainTimeline.to({}, { duration: 0.01 }, Number(dados.duracao_total));
    }

    await Promise.all(imagensParaCarregar);
    window.__HYPERFRAMES_READY__ = true;
}

inicializarComposicao();