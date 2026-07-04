// //  transition 

// document.addEventListener("click", function (event) {
//     const link = event.target.closest("a[href]");

//     if (!link) {
//         return;
//     }

//     const href = link.getAttribute("href");

//     if (
//         !href ||
//         href.startsWith("#") ||
//         href.startsWith("javascript:") ||
//         href.startsWith("mailto:") ||
//         href.startsWith("tel:") ||
//         link.target === "_blank" ||
//         link.hasAttribute("download")
//     ) {
//         return;
//     }

//     if (
//         event.defaultPrevented ||
//         event.button !== 0 ||
//         event.metaKey ||
//         event.ctrlKey ||
//         event.shiftKey ||
//         event.altKey
//     ) {
//         return;
//     }

//     const nextUrl = new URL(link.href, window.location.href);

//     if (nextUrl.origin !== window.location.origin) {
//         return;
//     }

//     event.preventDefault();

//     document.body.classList.add("page-transition-out");

//     setTimeout(function () {
//         window.location.href = link.href;
//     }, 220);
// });

// window.addEventListener("pageshow", function () {
//     document.body.classList.remove("page-transition-out");
// });