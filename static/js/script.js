const slides = document.querySelectorAll('.slide');
const dots = document.querySelectorAll('.dot');
const nextTrigger = document.querySelector('.next-trigger');

let currentIndex = 0;
let timer = null;

function gotoslide(index) {
    slides[currentIndex].classList.remove('active');
    dots[currentIndex].classList.remove('active');

    currentIndex = (index + slides.length) % slides.length;

    slides[currentIndex].classList.add('active');
    dots[currentIndex].classList.add('active');
}

function startAutoPlay() {
    timer = setInterval(() => {
        gotoslide(currentIndex + 1);
    }, 5000);  // 5s to change picture and the index will += 1
}

nextTrigger.addEventListener('click',() => {
    clearInterval(timer);
    gotoslide(currentIndex + 1);
    startAutoPlay();
})

startAutoPlay();

