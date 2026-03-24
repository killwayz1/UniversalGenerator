document.getElementById('generateForm').addEventListener('submit', async function(event) {
    event.preventDefault();

    const form = event.target;
    const button = document.getElementById('submitBtn');
    const resultBox = document.getElementById('resultBox');

    button.disabled = true;
    button.innerText = '⏳ Выкачиваю картинки, тексты и генерирую сайт...';
    
    resultBox.className = '';
    resultBox.style.display = 'none';
    resultBox.innerHTML = '';

    try {
        const formData = new FormData(form);
        
        const response = await fetch('/generate', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'success') {
            resultBox.className = 'success';
            
            // Выводим сообщение об успехе и кнопку для ручного скачивания
            resultBox.innerHTML = `
                ✅ ${data.message} <br><br>
                <a href="/download/${data.domain}" style="display: block; text-align: center; background: #10b981; color: white; padding: 12px; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 10px; transition: 0.2s;">
                    ⬇️ Скачать готовый архив сайта (.zip)
                </a>
            `;
            
            // Автоматическое скачивание архива
            window.location.href = `/download/${data.domain}`;
            
            form.reset();
        } else {
            resultBox.className = 'error';
            resultBox.innerText = `❌ Ошибка: ${data.message}`;
        }
    } catch (error) {
        resultBox.innerText = '❌ Произошла ошибка при соединении с локальным сервером. Проверьте, запущен ли app.py.';
        resultBox.className = 'error';
    } finally {
        button.disabled = false;
        button.innerText = 'Сгенерировать сайт';
    }
});