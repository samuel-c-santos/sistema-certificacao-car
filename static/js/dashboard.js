// Função para formatar números no padrão brasileiro (milhares com ponto e decimais com vírgula)
function formatNumberToBR(value) {
    return value.toLocaleString('pt-BR', { minimumFractionDigits: 4, maximumFractionDigits: 4 });
}

// Função para animar os números de maneira mais rápida para valores grandes
function animateNumbers(id, isFormatted = false) {
    const element = document.getElementById(id);
    const endValue = parseFloat(element.getAttribute('data-value')); // Lê o valor do atributo data-value
    let startValue = 0;
    const duration = 2000; // Duração da animação em milissegundos
    const frameRate = 60; // Número de frames por segundo
    const totalFrames = Math.round((duration / 1000) * frameRate); // Total de frames para a animação
    const increment = endValue / totalFrames; // Incremento por frame

    let currentFrame = 0;

    const timer = setInterval(() => {
        startValue += increment;
        currentFrame++;

        // Atualiza o valor exibido no elemento com formatação, se necessário
        if (isFormatted) {
            element.textContent = formatNumberToBR(startValue);
        } else {
            element.textContent = Math.floor(startValue);
        }

        // Verifica se já atingimos o total de frames ou o valor final
        if (currentFrame >= totalFrames || startValue >= endValue) {
            clearInterval(timer);
            // Garante que o valor final tenha a formatação correta
            element.textContent = isFormatted ? formatNumberToBR(endValue) : endValue;
        }
    }, 1000 / frameRate); // Tempo por frame
}

// Chama a função para cada número, aplicando formatação ao campo "Área Total Atingida"
animateNumbers('certificadosEmitidos');
animateNumbers('lotesGeracao');
animateNumbers('lotesAST');
animateNumbers('lotesIRU');
animateNumbers('areaTotal', true);  // Formatação para área total
animateNumbers('projetosAssentamento');