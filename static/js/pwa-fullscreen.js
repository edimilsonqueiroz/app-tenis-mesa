/**
 * PWA Fullscreen Handler
 * Gerencia fullscreen automático quando instalado como app
 */

// Detectar se está rodando como PWA instalado
function isPWAInstalled() {
  return window.navigator.standalone === true || 
         window.matchMedia('(display-mode: fullscreen)').matches ||
         window.matchMedia('(display-mode: standalone)').matches;
}

// Detectar se está no mobile
function isMobile() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// Forçar fullscreen ao entrar na página
function autoFullscreen() {
  if (!isMobile()) return;
  
  const elem = document.documentElement;
  
  // Tentar fullscreen nativo
  if (elem.requestFullscreen) {
    elem.requestFullscreen().catch(() => {});
  } else if (elem.webkitRequestFullscreen) {
    elem.webkitRequestFullscreen();
  } else if (elem.mozRequestFullScreen) {
    elem.mozRequestFullScreen();
  } else if (elem.msRequestFullscreen) {
    elem.msRequestFullscreen();
  }
}

// Esconder elementos desnecessários no mobile
function hideUIElements() {
  if (!isMobile()) return;
  
  // Tentar esconder a barra de endereço
  window.scrollTo(0, 1);
  
  // Adicionar class para CSS específico
  document.documentElement.classList.add('pwa-mode');
}

// Listener para quando a página entra em foco (ao voltar do lock screen)
document.addEventListener('visibilitychange', () => {
  if (document.hidden === false && isMobile()) {
    autoFullscreen();
  }
});

// Listener para orientação de tela
window.addEventListener('orientationchange', () => {
  if (isMobile()) {
    setTimeout(autoFullscreen, 500);
  }
});

// Ao carregar a página
document.addEventListener('DOMContentLoaded', () => {
  hideUIElements();
  if (isPWAInstalled() || isMobile()) {
    setTimeout(autoFullscreen, 100);
  }
});

// Também tentar quando janela ganhar foco
window.addEventListener('focus', () => {
  if (isMobile()) {
    autoFullscreen();
  }
});
