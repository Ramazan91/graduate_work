if ("Notification" in window) {    // Это строчка смотрит есть ли в браузере пуш
  Notification.requestPermission();  // это строчка делает запрос на разрешения уведомления

  function checkReminders() {  // ищим все элементы, у которых есть атрибут data-due
    const tasks = document.querySelectorAll("[data-due]");
    const now = new Date();

    tasks.forEach(task => {
      const due = new Date(task.dataset.due);
      if (!task.dataset.notified && due <= now) {
        new Notification("Напоминание", { body: task.dataset.title });
        task.dataset.notified = "true"; // чтобы не спамило
      }
    });
  }

  setInterval(checkReminders, 60000); // проверка каждую минуту
}

