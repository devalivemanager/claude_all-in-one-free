// 테스트용 스크립트: API 호출과 스크롤 등장 효과
fetch("/api/data")
  .then((res) => res.json())
  .then((data) => {
    const list = document.getElementById("products");
    for (const item of data.items) {
      const li = document.createElement("li");
      li.textContent = `${item.name} - ${item.price.toLocaleString("ko-KR")}원`;
      list.appendChild(li);
    }
  });

const observer = new IntersectionObserver((entries) => {
  for (const entry of entries) if (entry.isIntersecting) entry.target.classList.add("visible");
});
document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
