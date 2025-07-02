// Цей скрипт робить крол темінший коли його прокручують

document.addEventListener('DOMContentLoaded', () => {
  console.log('Scroll script loaded'); // Для дебагу
  const scrollElements = document.querySelectorAll('.custom-scroll');

  scrollElements.forEach((element) => {
    console.log('Found scroll element:', element); // Для дебагу
    let scrollTimeout;

    element.addEventListener('scroll', () => {
      element.classList.add('scrolling');
      console.log('Scrolling started on:', element); // Для дебагу
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        element.classList.remove('scrolling');
        console.log('Scrolling stopped on:', element); // Для дебагу
      }, 500);
    });
  });
});