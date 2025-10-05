if ("Notification" in window) {    // Проверяем, поддерживает ли браузер API уведомлений (Notification API)
  Notification.requestPermission();  // Запрашиваем у пользователя разрешение на показ уведомлений

  function checkReminders() {  // Функция для проверки напоминаний по задачам
    const tasks = document.querySelectorAll("[data-due]"); // Находим все элементы, у которых есть атрибут data-due (дата выполнения)
    const now = new Date(); // Получаем текущие дату и время

    tasks.forEach(task => { // Перебираем каждую задачу из найденных
      const due = new Date(task.dataset.due); // Преобразуем значение атрибута data-due в объект Date
      if (!task.dataset.notified && due <= now) { // Проверяем, не было ли уже уведомления и наступил ли срок задачи
        new Notification("Напоминание", { body: task.dataset.title }); // Показываем уведомление с заголовком задачи
        task.dataset.notified = "true"; // Помечаем задачу как уведомлённую, чтобы не показывать уведомление снова
      }
    });
  }

  setInterval(checkReminders, 60000); // Запускаем проверку каждые 60 секунд (1 минута)
}
