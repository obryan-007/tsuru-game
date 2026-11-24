"""
TSURU — Sobre os Ventos do Crepúsculo.

Jogo estilo Flappy Bird artesanal inspirado em gravuras Ukiyo-e e origami.
Implementado em um único arquivo Python com Pygame, sem imagens ou áudios
externos: todos os elementos (dobraduras 2.5D do tsuru, rastro de seda,
portais com talismãs ao vento, lanternas flutuantes, parallax crepuscular e
áudio pentatônico estilo koto/taiko) são gerados proceduralmente.
"""

from __future__ import annotations  # Permite anotações de tipo adiantadas (strings/forward refs)

import array  # Cria buffers binários de áudio PCM 16-bit sem depender do NumPy
import json  # Serializa e lê o arquivo de recorde local em formato JSON
import math  # Funções trigonométricas (seno, cosseno, tau, hipotenusa) para animações e som
import random  # Gera posições, cores de pétalas e variações procedurais aleatórias
from enum import Enum, auto  # Cria enumerações seguras para a máquina de estados do jogo
from pathlib import Path  # Manipula caminhos de arquivo de forma independente do sistema operacional
from typing import Dict, List, Tuple  # Tipos genéricos para documentação e checagem estática

import pygame # Biblioteca principal de janela, gráficos 2D, eventos, fontes e áudio


# =============================================================================
# CONSTANTES DE SIMULAÇÃO E CONFIGURAÇÃO
# =============================================================================

SCREEN_WIDTH: int = 500  # Largura fixa da janela do jogo em pixels
SCREEN_HEIGHT: int = 740  # Altura total da janela do jogo em pixels
GROUND_HEIGHT: int = 96  # Altura da faixa de chão na parte inferior da tela
PLAYABLE_HEIGHT: int = SCREEN_HEIGHT - GROUND_HEIGHT  # Área aérea útil onde o tsuru voa
FPS: int = 60  # Taxa máxima de atualização travada em 60 quadros por segundo
MAX_DT: float = 0.05  # Teto de Delta Time (50 ms) para evitar saltos físicos se o PC travar

GRAVITY: float = 1520.0  # Aceleração gravitacional aplicada ao tsuru (pixels/s²)
JUMP_VELOCITY: float = -485.0  # Velocidade vertical instantânea aplicada ao bater asas (para cima)
MAX_FALL_SPEED: float = 650.0  # Velocidade terminal máxima de queda livre (pixels/s)

BASE_SCROLL_SPEED: float = 198.0  # Velocidade horizontal inicial do cenário e dos portais (pixels/s)
MAX_SCROLL_SPEED: float = 288.0  # Velocidade horizontal máxima atingida em pontuações altas
GATE_WIDTH: int = 74  # Largura da coluna de cada portal do santuário (pixels)
BASE_GATE_GAP: int = 172  # Abertura vertical inicial entre o pilar superior e o inferior
MIN_GATE_GAP: int = 136  # Abertura mínima em níveis avançados para manter o jogo justo
GATE_SPAWN_INTERVAL: float = 1.58  # Intervalo base em segundos entre a criação de dois portais

# Caminho absoluto para o arquivo JSON salvo na mesma pasta deste script Python
HIGHSCORE_FILE: Path = Path(__file__).resolve().parent / "tsuru_save.json"


class GameState(Enum):
    """Estados da máquina de estados principal."""

    MENU = auto()       # Tela inicial com demonstração automática ao fundo
    JOGANDO = auto()    # Partida ativa controlada pelo jogador
    PAUSADO = auto()    # Jogo congelado exibindo opções de pausa
    GAME_OVER = auto()  # Tela de fim de voo com placar, recorde e reinício


class Palette:
    """Paleta crepuscular Ukiyo-e / Origami (sem cores primárias puras)."""

    # Céu crepuscular (gradiente de índigo -> ameixa -> terracota -> damasco suave)
    SKY_ZENITH = (25, 31, 56)       # #191F38 Azul-índigo noturno no topo do céu
    SKY_MID = (64, 49, 86)          # #403156 Tom ameixa intermediário do entardecer
    SKY_HORIZON = (196, 102, 78)    # #C4664E Terracota quente próximo ao horizonte
    SKY_GLOW = (240, 178, 122)      # #F0B27A Damasco dourado na linha do horizonte

    # Sol poente, cadeias de montanhas e solo
    SUN_CORE = (249, 224, 178)      # #F9E0B2 Creme luminoso do disco solar
    SUN_RING = (232, 137, 94)       # #E8895E Coral usado no halo externo do sol
    MOUNTAIN_FAR = (47, 45, 76)     # #2F2D4C Silhueta da cadeia de montanhas distante
    MOUNTAIN_MID = (34, 34, 58)     # #22223A Silhueta da cadeia de montanhas intermediária
    BAMBOO_SILHOUETTE = (24, 26, 42)  # #181A2A Silhueta escura dos bambuzais em parallax
    GROUND_INK = (19, 22, 34)       # #131622 Tinta escura sumi-e do solo
    GROUND_RIM = (78, 66, 88)       # #4E4258 Borda mineral que separa o chão do horizonte

    # Origami Tsuru (facetas de papel dobrado e ornamentos)
    PAPER_LIGHT = (246, 239, 226)   # #F6EFE2 Papel washi claro iluminado pelo sol
    PAPER_MID = (224, 212, 194)     # #E0D4C2 Tom intermediário das dobras e pescoço
    PAPER_SHADOW = (186, 170, 152)  # #BAAA98 Face inferior sombreada do origami
    WING_ACCENT = (214, 108, 86)    # #D66C56 Lacre coral-vermelho na borda das asas e colisão
    GOLD_FOIL = (232, 184, 92)      # #E8B85C Folha de ouro para bico, lanternas e recordes
    RIBBON_SILK = (244, 206, 148)   # #F4CE94 Tom de seda translúcida do rastro do tsuru

    # Portais do santuário e talismãs
    PILLAR_DARK = (30, 34, 52)      # #1E2234 Base escura de pedra/madeira dos portais
    PILLAR_MID = (48, 52, 78)       # #30344E Faixa chanfrada iluminada nos pilares
    PILLAR_WARM = (128, 84, 92)     # #80545C Reflexo quente do pôr do sol na borda direita
    OFUDA_PAPER = (238, 226, 206)   # #EEE2CE Papel dos talismãs pendurados ao vento
    OFUDA_SEAL = (206, 88, 72)      # #CE5848 Carimbo escarlate no centro do talismã
    JADE_MIST = (88, 168, 142)      # #58A88E Verde jade para indicar harmonia e precisão

    # Interface, textos e partículas atmosféricas
    TEXT_CREAM = (246, 240, 229)    # #F6F0E5 Branco papel suave para leitura confortável
    TEXT_MUTED = (174, 168, 182)    # #AEA8B6 Lavanda acinzentado para textos secundários
    INK_SHADOW = (12, 13, 22)       # #0C0D16 Cor escura usada em sombras projetadas
    CARD_BG = (24, 26, 42)          # #181A2A Fundo dos cartões translúcidos da UI
    PETAL_ROSE = (236, 156, 148)    # #EC9C94 Pétala rosada de cerejeira
    PETAL_GOLD = (242, 198, 122)    # #F2C67A Folha/pétala dourada de outono


# =============================================================================
# UTILITÁRIOS MATEMÁTICOS E CACHE DE TEXTURAS PROCEDURAIS
# =============================================================================

def lerp(start: float, end: float, factor: float) -> float:
    """Interpolação linear limitada ao intervalo [0, 1]."""
    t = max(0.0, min(1.0, factor))  # Garante que o fator de mistura não ultrapasse 0 ou 1
    return start + (end - start) * t  # Calcula o valor intermediário proporcional entre start e end


def ease_out_cubic(t: float) -> float:
    """Curva de suavização cúbica para entradas de interface."""
    clamped = max(0.0, min(1.0, t))  # Restringe o progresso normalizado entre 0.0 e 1.0
    return 1.0 - (1.0 - clamped) ** 3  # Começa rápido e desacelera suavemente ao final


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Restringe um valor ao intervalo [minimum, maximum]."""
    return max(minimum, min(maximum, value))  # Retorna minimum ou maximum se o valor sair dos limites


# Dicionário em memória que guarda superfícies de brilho já desenhadas para evitar recálculo a cada frame
_GLOW_CACHE: Dict[Tuple[int, Tuple[int, int, int], int], pygame.Surface] = {}


def get_glow_surface(
    radius: int,
    color: Tuple[int, int, int],
    max_alpha: int = 100,
) -> pygame.Surface:
    """Cria e armazena em cache uma aura radial suave com transparência."""
    safe_r = max(4, int(radius))  # Garante um raio mínimo de 4 px para evitar superfície inválida
    key = (safe_r, color, int(max_alpha))  # Monta chave única com raio, cor RGB e opacidade máxima
    if key in _GLOW_CACHE:  # Verifica se essa aura já foi gerada anteriormente
        return _GLOW_CACHE[key]  # Reutiliza a superfície pronta do cache para manter 60 FPS

    size = safe_r * 2  # Define lado do quadrado que comporta o círculo completo do brilho
    surf = pygame.Surface((size, size), pygame.SRCALPHA)  # Cria superfície com canal alfa (transparência)
    layers = max(8, min(20, safe_r // 3))  # Define quantos círculos concêntricos formam o gradiente
    for i in range(layers, 0, -1):  # Desenha do círculo maior (externo) para o menor (centro)
        ratio = i / layers  # Fração atual do raio (vai de 1.0 na borda até próximo de 0 no centro)
        r = max(1, int(safe_r * ratio))  # Raio em pixels da camada concêntrica atual
        alpha = int(max_alpha * ((1.0 - ratio) ** 1.9) * 0.42)  # Curva não-linear que concentra luz no centro
        if alpha > 0:  # Só desenha se houver opacidade visível
            pygame.draw.circle(surf, (*color, min(255, alpha)), (safe_r, safe_r), r)  # Pinta camada translúcida

    _GLOW_CACHE[key] = surf  # Salva a aura recém-gerada no cache global
    return surf  # Retorna a superfície pronta para ser aplicada com blit


def draw_text_with_shadow(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: Tuple[int, int, int],
    center: Tuple[int, int],
    shadow_offset: Tuple[int, int] = (2, 3),
    alpha: int = 255,
) -> pygame.Rect:
    """Desenha texto editorial com sombra suave projetada."""
    shadow_surf = font.render(text, True, Palette.INK_SHADOW)  # Renderiza o mesmo texto na cor de sombra
    text_surf = font.render(text, True, color)  # Renderiza o texto principal com antialiasing (True)

    if alpha < 255:  # Se o texto estiver em fade-in/fade-out, aplica transparência às duas camadas
        shadow_surf.set_alpha(int(alpha * 0.6))  # Sombra levemente mais transparente que o texto principal
        text_surf.set_alpha(alpha)  # Opacidade exata do texto principal

    rect = text_surf.get_rect(center=center)  # Calcula o retângulo centralizado na coordenada pedida
    shadow_rect = shadow_surf.get_rect(
        center=(center[0] + shadow_offset[0], center[1] + shadow_offset[1])  # Desloca a sombra em X e Y
    )
    surface.blit(shadow_surf, shadow_rect)  # Desenha primeiro a sombra por baixo
    surface.blit(text_surf, rect)  # Desenha o texto nítido por cima da sombra
    return rect  # Retorna a área ocupada pelo texto na tela


# =============================================================================
# SÍNTESE SONORA PENTATÔNICA (KOTO / SINO / TAIKO / BRISA)
# =============================================================================

class SoundManager:
    """Sintetiza efeitos musicais orgânicos em PCM 16-bit sem arquivos externos."""

    SAMPLE_RATE: int = 44100  # Taxa padrão de amostragem de áudio (44.1 kHz)
    # Frequências em Hz da escala pentatônica japonesa (Yo): D5, E5, G5, A5, B5, D6, E6
    PENTATONIC_HZ: Tuple[float, ...] = (
        587.33,  # Ré5
        659.25,  # Mi5
        783.99,  # Sol5
        880.00,  # Lá5
        987.77,  # Si5
        1174.66,  # Ré6
        1318.51,  # Mi6
    )

    def __init__(self) -> None:
        self.enabled: bool = False  # Indica se o sistema de áudio do Pygame iniciou com sucesso
        self.muted: bool = False  # Controla se o jogador silenciou os sons pela tecla M ou ícone
        self._sounds: Dict[str, pygame.mixer.Sound] = {}  # Guarda efeitos nomeados (asa, colisão, etc.)
        self._koto_notes: List[pygame.mixer.Sound] = []  # Lista de notas musicais da escala pentatônica
        self._init_audio()  # Tenta inicializar o mixer e gerar os sons em memória

    def _init_audio(self) -> None:
        """Inicializa o mixer com fallback seguro para ambientes sem áudio."""
        try:
            if not pygame.mixer.get_init():  # Evita reinicializar caso o mixer já esteja ativo
                pygame.mixer.init(
                    frequency=self.SAMPLE_RATE,  # Define 44100 amostras por segundo
                    size=-16,  # Áudio PCM assinado de 16 bits (-32768 a 32767)
                    channels=1,  # Canal mono (ideal e leve para efeitos sintetizados)
                    buffer=512,  # Buffer pequeno para baixa latência ao bater asas
                )
            self.enabled = True  # Marca o áudio como disponível
            self._build_sounds()  # Sintetiza todos os efeitos sonoros na inicialização
        except pygame.error:
            self.enabled = False  # Caso não exista placa de som, o jogo segue mudo sem quebrar

    def _synth_koto_pluck(self, freq: float, duration: float = 0.42) -> pygame.mixer.Sound:
        """Simula corda dedilhada quente (fundamental + 2º e 3º harmônicos)."""
        total = max(1, int(self.SAMPLE_RATE * duration))  # Quantidade total de amostras do som
        samples = array.array("h")  # Vetor de inteiros 16-bit com sinal ('h' = signed short)
        attack = max(1, int(total * 0.018))  # Duração do ataque inicial (1.8%) para evitar estalos
        p1 = p2 = p3 = 0.0  # Acumuladores de fase para a fundamental e os dois harmônicos

        for i in range(total):  # Gera amostra por amostra ao longo da duração do som
            t = i / total  # Progresso normalizado do áudio (0.0 no início até 1.0 no fim)
            p1 += (2.0 * math.pi * freq) / self.SAMPLE_RATE  # Avança fase da frequência principal
            p2 += (2.0 * math.pi * freq * 2.0) / self.SAMPLE_RATE  # Avança fase da 1ª oitava acima
            p3 += (2.0 * math.pi * freq * 3.0) / self.SAMPLE_RATE  # Avança fase do 3º harmônico

            # Harmônicos agudos decaem mais rápido que a nota fundamental, imitando corda real
            body = (
                math.sin(p1) * 0.68  # Corpo principal da nota
                + math.sin(p2) * 0.22 * ((1.0 - t) ** 2.2)  # Brilho do 2º harmônico com decay rápido
                + math.sin(p3) * 0.10 * ((1.0 - t) ** 3.5)  # Toque metálico inicial do 3º harmônico
            )
            env = min(1.0, i / attack) * ((1.0 - t) ** 2.3)  # Envelope: sobe no ataque e cai suavemente
            val = int(clamp(body * env * 0.28, -1.0, 1.0) * 32767)  # Converte float [-1, 1] para PCM 16-bit
            samples.append(val)  # Anexa amostra ao buffer

        return pygame.mixer.Sound(buffer=samples)  # Cria objeto Sound direto da memória RAM

    def _synth_paper_wing(self) -> pygame.mixer.Sound:
        """Gera um farfalhar suave de papel e brisa ao bater asas."""
        duration = 0.13  # Som curto e leve de 130 milissegundos
        total = int(self.SAMPLE_RATE * duration)  # Número total de amostras para 0.13s
        samples = array.array("h")  # Buffer PCM de 16 bits
        phase = 0.0  # Fase do oscilador senoidal
        lp_noise = 0.0  # Estado do filtro passa-baixa para suavizar o ruído branco

        for i in range(total):
            t = i / total  # Progresso do som entre 0.0 e 1.0
            freq = lerp(240.0, 410.0, t)  # Tom sobe levemente para dar sensação de impulso para cima
            phase += (2.0 * math.pi * freq) / self.SAMPLE_RATE  # Incrementa ângulo da onda senoidal
            lp_noise = lerp(lp_noise, random.uniform(-1.0, 1.0), 0.18)  # Suaviza ruído para soar como papel
            tone = math.sin(phase) * 0.35 + lp_noise * 0.65  # Mistura sopro tonal com farfalhar de papel
            env = math.sin(t * math.pi) ** 1.4  # Envelope em arco (começa e termina em zero sem clique)
            samples.append(int(clamp(tone * env * 0.24, -1.0, 1.0) * 32767))  # Grava amostra escalada

        return pygame.mixer.Sound(buffer=samples)  # Constrói efeito sonoro pronto para tocar

    def _synth_taiko_impact(self) -> pygame.mixer.Sound:
        """Gera batida grave de tambor taiko + estalo de papel na colisão."""
        duration = 0.38  # Duração de 380 ms para reverberação grave
        total = int(self.SAMPLE_RATE * duration)  # Total de amostras
        samples = array.array("h")  # Buffer PCM 16-bit
        phase = 0.0  # Fase do oscilador grave
        lp_noise = 0.0  # Ruído filtrado simulando impacto seco

        for i in range(total):
            t = i / total  # Progresso normalizado
            freq = lerp(145.0, 44.0, t ** 0.55)  # Queda rápida de frequência típica de pele de tambor
            phase += (2.0 * math.pi * freq) / self.SAMPLE_RATE  # Atualiza fase do grave
            lp_noise = lerp(lp_noise, random.uniform(-1.0, 1.0), 0.25)  # Ruído abafado do choque
            # Tanh aplica saturação analógica quente no grave do tambor
            drum = math.tanh(1.6 * math.sin(phase)) * 0.72 + lp_noise * 0.28 * ((1.0 - t) ** 2.5)
            env = min(1.0, i / 120.0) * ((1.0 - t) ** 1.9)  # Ataque firme seguido de decaimento natural
            samples.append(int(clamp(drum * env * 0.42, -1.0, 1.0) * 32767))  # Converte para 16-bit

        return pygame.mixer.Sound(buffer=samples)

    def _synth_lantern_chime(self) -> pygame.mixer.Sound:
        """Acorde cristalino de sino de vento ao coletar uma lanterna."""
        duration = 0.45  # Duração total do acorde
        total = int(self.SAMPLE_RATE * duration)  # Total de amostras no buffer
        buf = [0.0] * total  # Buffer temporário em float para somar duas notas sobrepostas
        notes = [(880.0, 0.0, 0.32), (1318.51, 0.055, 0.38)]  # Notas Lá5 e Mi6 com leve atraso (arpejo)

        for freq, start_s, note_dur in notes:  # Sintetiza cada nota separadamente dentro do buffer
            start_idx = int(start_s * self.SAMPLE_RATE)  # Índice inicial da nota em amostras
            length = int(note_dur * self.SAMPLE_RATE)  # Duração da nota em amostras
            phase = 0.0  # Fase inicial zerada para a nota
            for j in range(length):
                pos = start_idx + j  # Posição exata no buffer combinado
                if pos >= total:  # Impede escrita além do final do buffer
                    break
                p = j / length  # Progresso local dessa nota
                phase += (2.0 * math.pi * freq) / self.SAMPLE_RATE  # Avança fase da frequência
                val = math.sin(phase) * 0.75 + math.sin(phase * 2.0) * 0.25  # Fundamental + oitava brilhante
                env = min(1.0, j / 240.0) * ((1.0 - p) ** 2.1)  # Ataque suave e cauda ressonante
                buf[pos] += val * env  # Soma ao buffer preservando sobreposição harmônica

        samples = array.array("h")  # Converte o buffer float somado para inteiros de 16 bits
        for v in buf:
            samples.append(int(clamp(v * 0.20, -1.0, 1.0) * 32767))
        return pygame.mixer.Sound(buffer=samples)

    def _build_sounds(self) -> None:
        """Pré-gera todos os instrumentos e efeitos em memória."""
        self._sounds["wing"] = self._synth_paper_wing()  # Som de bater asas
        self._sounds["hit"] = self._synth_taiko_impact()  # Som de colisão
        self._sounds["lantern"] = self._synth_lantern_chime()  # Som de coleta da lanterna
        self._sounds["click"] = self._synth_koto_pluck(987.77, duration=0.14)  # Clique sutil de botão
        self._koto_notes = [  # Gera uma nota de koto para cada grau da escala pentatônica
            self._synth_koto_pluck(freq, duration=0.45)
            for freq in self.PENTATONIC_HZ
        ]

    def play(self, name: str) -> None:
        """Toca um efeito sonoro nomeado caso o som esteja ativo."""
        if not self.enabled or self.muted:  # Não toca se estiver mudo ou sem driver de áudio
            return
        snd = self._sounds.get(name)  # Busca o som no dicionário
        if snd is not None:
            snd.play()  # Reproduz o som de forma assíncrona no mixer

    def play_pentatonic(self, streak_index: int) -> None:
        """Toca uma nota ascendente da escala pentatônica conforme a sequência."""
        if not self.enabled or self.muted or not self._koto_notes:  # Aborta se áudio estiver desativado
            return
        idx = clamp(streak_index, 0, len(self._koto_notes) - 1)  # Limita o índice ao tamanho da escala
        self._koto_notes[int(idx)].play()  # Toca a nota correspondente ao combo atual de harmonia

    def toggle_mute(self) -> bool:
        """Alterna o estado de mudo e retorna o estado atual."""
        self.muted = not self.muted  # Inverte True/False
        return self.muted  # Retorna o novo estado para eventual uso pela interface


# =============================================================================
# PERSISTÊNCIA EM JSON
# =============================================================================

class HighScoreManager:
    """Armazena recorde de pontuação e melhor sequência em arquivo JSON local."""

    def __init__(self, filepath: Path = HIGHSCORE_FILE) -> None:
        self.filepath = filepath  # Caminho do arquivo JSON onde os dados serão persistidos
        self.high_score: int = 0  # Maior pontuação já alcançada
        self.best_streak: int = 0  # Maior sequência de Harmonia já alcançada
        self._load()  # Carrega valores salvos anteriormente, se existirem

    def _load(self) -> None:
        """Lê os dados salvos de forma resiliente."""
        try:
            if self.filepath.exists():  # Só tenta abrir se o arquivo já existir no disco
                data = json.loads(self.filepath.read_text(encoding="utf-8"))  # Lê e decodifica o JSON
                self.high_score = max(0, int(data.get("high_score", 0)))  # Garante valor >= 0
                self.best_streak = max(0, int(data.get("best_streak", 0)))  # Garante valor >= 0
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.high_score = 0  # Em caso de arquivo corrompido ou ilegível, reseta com segurança
            self.best_streak = 0

    def update(self, score: int, max_streak: int) -> bool:
        """Salva novos recordes caso tenham sido superados. Retorna True se bateu recorde."""
        new_record = score > self.high_score  # Verifica se houve novo recorde de pontuação
        streak_improved = max_streak > self.best_streak  # Verifica se houve nova melhor sequência
        if new_record:
            self.high_score = score  # Atualiza recorde em memória
        if streak_improved:
            self.best_streak = max_streak  # Atualiza melhor sequência em memória

        if new_record or streak_improved:  # Só grava no disco quando algum recorde de fato mudou
            try:
                payload = {
                    "high_score": self.high_score,
                    "best_streak": self.best_streak,
                }
                self.filepath.write_text(
                    json.dumps(payload, indent=2),  # Formata JSON legível com indentação de 2 espaços
                    encoding="utf-8",
                )
            except OSError:
                pass  # Ignora falha de gravação (ex.: pasta somente leitura) sem travar o jogo
        return new_record  # Informa se deve exibir o destaque de "NOVO RECORDE"


# =============================================================================
# CÂMERA E SISTEMA DE PARTÍCULAS ORGÂNICAS
# =============================================================================

class CameraShake:
    """Tremor de câmera baseado em trauma com decaimento exponencial suave."""

    def __init__(self) -> None:
        self.trauma: float = 0.0  # Nível de intensidade do tremor entre 0.0 e 1.0
        self.max_offset: float = 15.0  # Deslocamento máximo em pixels aplicado na câmera
        self.offset_x: float = 0.0  # Deslocamento horizontal calculado neste quadro
        self.offset_y: float = 0.0  # Deslocamento vertical calculado neste quadro

    def add_trauma(self, amount: float) -> None:
        """Acumula trauma de impacto no intervalo [0, 1]."""
        self.trauma = clamp(self.trauma + amount, 0.0, 1.0)  # Soma e trava no limite máximo 1.0

    def update(self, dt: float) -> None:
        """Atualiza o tremor proporcional ao quadrado do trauma."""
        if self.trauma > 0.0:
            intensity = self.trauma ** 2  # Elevar ao quadrado torna impactos fortes bem mais visíveis
            self.offset_x = random.uniform(-1.0, 1.0) * self.max_offset * intensity  # Vibração X aleatória
            self.offset_y = random.uniform(-1.0, 1.0) * self.max_offset * intensity  # Vibração Y aleatória
            self.trauma = max(0.0, self.trauma - dt * 2.5)  # Reduz trauma continuamente até zerar
        else:
            self.offset_x = 0.0  # Sem trauma, câmera fica perfeitamente estática
            self.offset_y = 0.0

    def get_offset(self) -> Tuple[int, int]:
        """Retorna deslocamento inteiro da câmera para o frame atual."""
        return (int(round(self.offset_x)), int(round(self.offset_y)))  # Arredonda para coordenadas de pixel


class Particle:
    """Partícula versátil: pode ser pétala giratória, brasa dourada ou faísca de papel."""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: Tuple[int, int, int],
        size: float,
        lifetime: float,
        gravity: float = 210.0,
        kind: str = "ember",
    ) -> None:
        self.x = x  # Posição horizontal atual
        self.y = y  # Posição vertical atual
        self.vx = vx  # Velocidade horizontal (pixels/s)
        self.vy = vy  # Velocidade vertical (pixels/s)
        self.color = color  # Cor RGB da partícula
        self.start_size = size  # Tamanho inicial para calcular encolhimento gradual
        self.size = size  # Tamanho atual em pixels
        self.lifetime = lifetime  # Tempo total de vida em segundos
        self.age = 0.0  # Idade acumulada da partícula
        self.gravity = gravity  # Gravidade individual (pétalas caem mais devagar que brasas)
        self.kind = kind  # Tipo visual: "petal" (losango giratório) ou "ember" (ponto luminoso)
        self.rot = random.uniform(0.0, math.tau)  # Ângulo inicial aleatório em radianos
        self.rot_speed = random.uniform(-6.0, 6.0)  # Velocidade de giro da pétala (rad/s)

    @property
    def alive(self) -> bool:
        """Indica se a partícula continua ativa."""
        return self.age < self.lifetime  # Permanece viva enquanto não atingir o tempo limite

    def update(self, dt: float) -> None:
        """Atualiza física com resistência do ar e rotação."""
        self.age += dt  # Avança o tempo de vida
        self.vy += self.gravity * dt  # Aplica gravidade na velocidade vertical
        drag = max(0.0, 1.0 - (2.6 if self.kind == "petal" else 1.7) * dt)  # Fator de desaceleração do ar
        self.vx *= drag  # Freia movimento horizontal gradualmente
        if self.kind == "petal":
            self.vx += math.sin(self.age * 6.0 + self.rot) * 32.0 * dt  # Oscilação lateral suave no vento
        self.x += self.vx * dt  # Atualiza posição X
        self.y += self.vy * dt  # Atualiza posição Y
        self.rot += self.rot_speed * dt  # Gira a partícula

        progress = clamp(self.age / self.lifetime, 0.0, 1.0)  # Percentual de vida já consumido
        self.size = max(1.0, self.start_size * (1.0 - progress * 0.75))  # Encolhe até 25% do tamanho

    def draw(self, fx_surface: pygame.Surface, offset: Tuple[int, int]) -> None:
        """Desenha a partícula na camada de transparência."""
        progress = clamp(self.age / self.lifetime, 0.0, 1.0)  # Percentual de vida (0 a 1)
        alpha = int(240 * (1.0 - progress ** 1.3))  # Transparência desaparece suavemente no final
        if alpha <= 0:
            return

        px = self.x + offset[0]  # Posição X compensada pelo tremor da câmera
        py = self.y + offset[1]  # Posição Y compensada pelo tremor da câmera

        if self.kind == "petal":
            # Calcula 4 vértices de um losango inclinado pelo ângulo self.rot
            s = self.size
            dx_a, dy_a = math.cos(self.rot) * s * 1.4, math.sin(self.rot) * s * 1.4
            dx_b, dy_b = math.cos(self.rot + 1.4) * s * 0.65, math.sin(self.rot + 1.4) * s * 0.65
            dx_c, dy_c = math.cos(self.rot - 1.4) * s * 0.65, math.sin(self.rot - 1.4) * s * 0.65
            pts = [
                (px + dx_a, py + dy_a),
                (px + dx_b, py + dy_b),
                (px - dx_a, py - dy_a),
                (px + dx_c, py + dy_c),
            ]
            pygame.draw.polygon(fx_surface, (*self.color, alpha), pts)  # Desenha pétala translúcida
        else:
            if self.size >= 2.2:  # Partículas maiores recebem aura luminosa ao redor
                glow = get_glow_surface(int(self.size * 2.6), self.color, int(alpha * 0.45))
                fx_surface.blit(
                    glow,
                    (int(px) - glow.get_width() // 2, int(py) - glow.get_height() // 2),
                )
            pygame.draw.circle(
                fx_surface,
                (*self.color, alpha),  # Cor com alfa na camada de efeitos
                (int(px), int(py)),
                max(1, int(self.size)),  # Raio mínimo de 1 px
            )


class Shockwave:
    """Onda concêntrica sutil para marcar batidas de asa, lanternas e colisões."""

    def __init__(
        self,
        x: float,
        y: float,
        color: Tuple[int, int, int],
        max_radius: float = 52.0,
        duration: float = 0.36,
        width: int = 2,
    ) -> None:
        self.x = x  # Centro X do anel
        self.y = y  # Centro Y do anel
        self.color = color  # Cor RGB da borda do anel
        self.max_radius = max_radius  # Raio final máximo da expansão
        self.duration = duration  # Duração total da animação em segundos
        self.width = width  # Espessura inicial do traço do círculo
        self.age = 0.0  # Tempo decorrido desde a criação

    @property
    def alive(self) -> bool:
        """Retorna True enquanto a onda ainda estiver visível."""
        return self.age < self.duration  # Ativa enquanto não concluir a duração

    def update(self, dt: float) -> None:
        """Avança o tempo da onda."""
        self.age += dt  # Soma o Delta Time do quadro atual

    def draw(self, fx_surface: pygame.Surface, offset: Tuple[int, int]) -> None:
        """Desenha o anel expansivo na camada alfa."""
        progress = clamp(self.age / self.duration, 0.0, 1.0)  # Progresso normalizado [0, 1]
        radius = max(2, int(lerp(5.0, self.max_radius, ease_out_cubic(progress))))  # Expande com desaceleração
        alpha = int(195 * (1.0 - progress))  # Fica transparente à medida que se expande
        if alpha > 0:
            pygame.draw.circle(
                fx_surface,
                (*self.color, alpha),
                (int(self.x + offset[0]), int(self.y + offset[1])),  # Centro com tremor de câmera
                radius,
                max(1, int(self.width * (1.0 - progress * 0.5))),  # Traço afina levemente ao expandir
            )


class FloatingText:
    """Chamada tipográfica flutuante para feedbacks de pontuação e harmonia."""

    def __init__(
        self,
        x: float,
        y: float,
        text: str,
        color: Tuple[int, int, int],
        font: pygame.font.Font,
        duration: float = 0.9,
    ) -> None:
        self.x = x  # Posição horizontal inicial
        self.y = y  # Posição vertical inicial
        self.text = text  # Conteúdo textual exibido (ex.: "+2 LANTERNA")
        self.color = color  # Cor RGB do texto
        self.font = font  # Fonte Pygame usada na renderização
        self.duration = duration  # Duração em segundos antes de desaparecer
        self.age = 0.0  # Idade atual em segundos

    @property
    def alive(self) -> bool:
        """Indica se o texto ainda está em tela."""
        return self.age < self.duration  # Continua na lista até expirar

    def update(self, dt: float) -> None:
        """Eleva o texto suavemente."""
        self.age += dt  # Avança cronômetro do texto
        self.y -= 42.0 * dt  # Flutua para cima a 42 pixels por segundo

    def draw(self, surface: pygame.Surface, offset: Tuple[int, int]) -> None:
        """Renderiza o texto com fade-out suave."""
        progress = clamp(self.age / self.duration, 0.0, 1.0)  # Progresso de vida
        alpha = int(255 * (1.0 - progress ** 1.6))  # Desaparece suavemente próximo ao fim
        if alpha > 0:
            draw_text_with_shadow(
                surface,
                self.font,
                self.text,
                self.color,
                (int(self.x + offset[0]), int(self.y + offset[1])),
                shadow_offset=(1, 2),
                alpha=alpha,
            )


# =============================================================================
# MUNDO PARALLAX: CÉU CREPUSCULAR, MONTANHAS, BAMBUS, PÉTALAS E RELVA
# =============================================================================

class ParallaxWorld:
    """Constrói atmosfera Ukiyo-e em camadas com profundidade e movimento vivo."""

    def __init__(self) -> None:
        self.sky_surface = self._build_twilight_sky()  # Céu em gradiente + sol pré-renderizado
        self.stars = self._create_stars(38)  # 38 estrelas sutis no topo do céu
        self.ambient_petals = self._create_ambient_petals(18)  # 18 pétalas contínuas ao vento
        self.far_mountains = self._build_mountain_tile(  # Camada distante (lenta) de montanhas
            color=Palette.MOUNTAIN_FAR, min_h=150, max_h=275, step=62
        )
        self.mid_mountains = self._build_mountain_tile(  # Camada intermediária de montanhas
            color=Palette.MOUNTAIN_MID, min_h=95, max_h=195, step=48
        )
        self.bamboo_layer = self._build_bamboo_tile()  # Camada mais próxima de bambus em silhueta
        self.grass_blades = self._create_grass_blades()  # Lâminas de capim na borda do solo

        self.far_offset: float = 0.0  # Deslocamento horizontal acumulado das montanhas distantes
        self.mid_offset: float = 0.0  # Deslocamento horizontal acumulado das montanhas médias
        self.bamboo_offset: float = 0.0  # Deslocamento horizontal acumulado dos bambus
        self.ground_offset: float = 0.0  # Deslocamento horizontal das texturas do solo
        self.elapsed: float = 0.0  # Tempo total decorrido para animações senoidais contínuas

    @staticmethod
    def _build_twilight_sky() -> pygame.Surface:
        """Pré-renderiza gradiente multi-ponto do crepúsculo + disco solar."""
        surf = pygame.Surface((SCREEN_WIDTH, PLAYABLE_HEIGHT))  # Superfície opaca do fundo do céu
        stops = [  # Pontos de parada (altura normalizada, cor RGB) do gradiente vertical
            (0.00, Palette.SKY_ZENITH),
            (0.45, Palette.SKY_MID),
            (0.82, Palette.SKY_HORIZON),
            (1.00, Palette.SKY_GLOW),
        ]
        for y in range(PLAYABLE_HEIGHT):  # Pinta linha por linha misturando entre duas cores vizinhas
            t = y / max(1, PLAYABLE_HEIGHT - 1)  # Posição vertical normalizada [0.0, 1.0]
            for idx in range(len(stops) - 1):
                t0, c0 = stops[idx]
                t1, c1 = stops[idx + 1]
                if t0 <= t <= t1:  # Encontra o segmento do gradiente correspondente à linha y
                    local = (t - t0) / max(0.0001, t1 - t0)  # Fração interna dentro do segmento
                    col = tuple(int(lerp(c0[k], c1[k], local)) for k in range(3))  # Interpola R, G e B
                    pygame.draw.line(surf, col, (0, y), (SCREEN_WIDTH, y))  # Desenha faixa horizontal
                    break

        # Grande sol poente estilizado à direita com halo suave
        sun_center = (int(SCREEN_WIDTH * 0.72), int(PLAYABLE_HEIGHT * 0.42))
        sun_glow = get_glow_surface(180, Palette.SUN_RING, max_alpha=95)  # Halo quente ao redor do sol
        sun_glow_pos = (
            sun_center[0] - sun_glow.get_width() // 2,
            sun_center[1] - sun_glow.get_height() // 2,
        )
        surf.blit(sun_glow, sun_glow_pos)  # Aplica brilho solar no céu
        pygame.draw.circle(surf, Palette.SUN_CORE, sun_center, 66)  # Desenha o disco solar sólido

        # Faixas sutis de nuvem atravessando o disco solar (estilo gravura Ukiyo-e)
        cloud_surf = pygame.Surface((SCREEN_WIDTH, PLAYABLE_HEIGHT), pygame.SRCALPHA)
        for cx, cy, cw, ch in (
            (sun_center[0] - 85, sun_center[1] + 18, 175, 11),
            (sun_center[0] - 40, sun_center[1] - 24, 130, 8),
        ):
            pygame.draw.rect(
                cloud_surf,
                (*Palette.SKY_HORIZON, 115),
                (cx, cy, cw, ch),
                border_radius=6,
            )
        surf.blit(cloud_surf, (0, 0))  # Funde as nuvens ao céu pré-renderizado
        return surf

    @staticmethod
    def _create_stars(count: int) -> List[Dict[str, float]]:
        """Estrelas sutis apenas na metade superior do céu índigo."""
        stars = []
        for _ in range(count):
            stars.append(
                {
                    "x": random.uniform(0, SCREEN_WIDTH),  # Posição X inicial espalhada
                    "y": random.uniform(10, PLAYABLE_HEIGHT * 0.42),  # Apenas na parte superior escura
                    "size": random.choice([1.0, 1.3, 1.8]),  # Raios variados para profundidade
                    "speed": random.uniform(4.0, 10.0),  # Movimento bem lento (muito distante)
                    "phase": random.uniform(0.0, math.tau),  # Fase individual de cintilação
                }
            )
        return stars

    @staticmethod
    def _create_ambient_petals(count: int) -> List[Dict[str, float]]:
        """Pétalas de cerejeira carregadas pela brisa do cenário."""
        petals = []
        for _ in range(count):
            petals.append(
                {
                    "x": random.uniform(0, SCREEN_WIDTH),  # Posição X inicial
                    "y": random.uniform(20, PLAYABLE_HEIGHT - 20),  # Posição Y inicial
                    "vx": random.uniform(-46.0, -22.0),  # Vento soprando para a esquerda
                    "vy": random.uniform(8.0, 24.0),  # Queda lenta e suave
                    "size": random.uniform(3.2, 5.4),  # Comprimento da pétala
                    "phase": random.uniform(0.0, math.tau),  # Fase única de giro e balanço
                    "color": random.choice([Palette.PETAL_ROSE, Palette.PETAL_GOLD]),  # Rosa ou dourada
                }
            )
        return petals

    @staticmethod
    def _build_mountain_tile(
        color: Tuple[int, int, int],
        min_h: int,
        max_h: int,
        step: int,
    ) -> Tuple[pygame.Surface, int]:
        """Gera silhueta contínua e repetível (seamless) de cadeias de montanhas."""
        tile_w = SCREEN_WIDTH * 2  # Largura dobrada para evitar repetições óbvias na tela
        surf = pygame.Surface((tile_w, PLAYABLE_HEIGHT), pygame.SRCALPHA)
        heights: List[int] = []
        count = tile_w // step  # Quantidade de picos/vértices ao longo do tile
        for _ in range(count):
            heights.append(random.randint(min_h, max_h))  # Sorteia altitude de cada pico
        heights.append(heights[0])  # Repete a primeira altura no fim para emenda contínua perfeita

        points = [(0, PLAYABLE_HEIGHT)]  # Canto inferior esquerdo para fechar o polígono
        for idx, h in enumerate(heights):
            px = int((idx / count) * tile_w)  # Distribui os vértices uniformemente na largura
            points.append((px, PLAYABLE_HEIGHT - h))  # Converte altura em coordenada Y de topo
        points.append((tile_w, PLAYABLE_HEIGHT))  # Canto inferior direito para fechar a silhueta

        pygame.draw.polygon(surf, color, points)  # Preenche a cadeia de montanhas

        # Neblina suave na base das montanhas para separar as camadas com profundidade
        mist = pygame.Surface((tile_w, 70), pygame.SRCALPHA)
        for row in range(70):
            alpha = int(42 * (row / 70.0))  # Névoa fica mais densa perto do chão
            pygame.draw.line(mist, (*Palette.SKY_GLOW, alpha), (0, row), (tile_w, row))
        surf.blit(mist, (0, PLAYABLE_HEIGHT - 70))
        return surf, tile_w

    @staticmethod
    def _build_bamboo_tile() -> Tuple[pygame.Surface, int]:
        """Cria grupos espaçados de bambus e ramos ao longo do vale."""
        tile_w = SCREEN_WIDTH * 2  # Largura de duas telas para rolagem contínua
        surf = pygame.Surface((tile_w, PLAYABLE_HEIGHT), pygame.SRCALPHA)
        x = 35
        while x < tile_w - 40:
            cluster_size = random.randint(2, 4)  # Cada moita tem de 2 a 4 caules
            for _ in range(cluster_size):
                bx = x + random.randint(-14, 14)  # Posição horizontal do caule na moita
                bh = random.randint(120, 235)  # Altura do bambu
                lean = random.randint(-14, 14)  # Inclinação natural para esquerda ou direita
                top_y = PLAYABLE_HEIGHT - bh  # Coordenada Y da ponta do bambu
                pygame.draw.line(
                    surf,
                    (*Palette.BAMBOO_SILHOUETTE, 165),
                    (bx, PLAYABLE_HEIGHT),
                    (bx + lean, top_y),
                    random.choice([3, 4]),  # Espessura do caule
                )
                for seg in range(1, 5):  # Adiciona folhas em nós intermediários do caule
                    frac = seg / 5.0
                    nx = int(lerp(bx, bx + lean, frac))  # X do nó ao longo da inclinação
                    ny = int(lerp(PLAYABLE_HEIGHT, top_y, frac))  # Y do nó
                    if seg % 2 == 0:
                        leaf_dir = 1 if (seg + bx) % 2 == 0 else -1  # Alterna lado da folha
                        pygame.draw.polygon(
                            surf,
                            (*Palette.BAMBOO_SILHOUETTE, 150),
                            [
                                (nx, ny),
                                (nx + 18 * leaf_dir, ny - 6),
                                (nx + 10 * leaf_dir, ny + 3),
                            ],
                        )
            x += random.randint(155, 240)  # Espaço aberto até o próximo grupo de bambus
        return surf, tile_w

    @staticmethod
    def _create_grass_blades() -> List[Dict[str, float]]:
        """Folhas de capim na borda do chão que balançam ao vento."""
        blades = []
        for x in range(-12, SCREEN_WIDTH + 48, 12):  # Distribui uma folha a cada 12 pixels
            blades.append(
                {
                    "x": float(x),  # Posição X contínua (permite scroll sem saltos)
                    "height": random.uniform(10.0, 22.0),  # Altura individual de cada folha
                    "phase": random.uniform(0.0, math.tau),  # Fase de balanço independente
                }
            )
        return blades

    def update(self, dt: float, scroll_speed: float) -> None:
        """Move camadas do parallax, pétalas e vento conforme Delta Time."""
        self.elapsed += dt  # Acumula tempo total para funções senoidais

        # Cada camada se move a uma fração diferente da velocidade principal (efeito Parallax)
        self.far_offset = (self.far_offset + scroll_speed * 0.12 * dt) % self.far_mountains[1]
        self.mid_offset = (self.mid_offset + scroll_speed * 0.28 * dt) % self.mid_mountains[1]
        self.bamboo_offset = (self.bamboo_offset + scroll_speed * 0.48 * dt) % self.bamboo_layer[1]
        self.ground_offset = (self.ground_offset + scroll_speed * dt) % 48.0  # 1.0x velocidade real

        for star in self.stars:  # Move estrelas bem devagar e recicla na borda direita
            star["x"] -= star["speed"] * dt
            if star["x"] < -4:
                star["x"] = SCREEN_WIDTH + 4
                star["y"] = random.uniform(10, PLAYABLE_HEIGHT * 0.42)

        for petal in self.ambient_petals:  # Move pétalas com vento e ondulação vertical
            petal["x"] += petal["vx"] * dt
            sway_y = math.sin(self.elapsed * 2.2 + petal["phase"]) * 14.0  # Turbulência leve do ar
            petal["y"] += (petal["vy"] + sway_y) * dt
            if petal["x"] < -12 or petal["y"] > PLAYABLE_HEIGHT + 8:  # Recicla pétala que saiu da tela
                petal["x"] = random.uniform(SCREEN_WIDTH * 0.35, SCREEN_WIDTH + 30)
                petal["y"] = random.uniform(-20.0, PLAYABLE_HEIGHT * 0.45)

        for blade in self.grass_blades:  # Rola as folhas de capim na velocidade exata do solo
            blade["x"] -= scroll_speed * dt
            if blade["x"] < -24.0:
                blade["x"] += SCREEN_WIDTH + 60.0  # Reposiciona à direita sem perder altura/fase

    def draw_backdrop(
        self,
        surface: pygame.Surface,
        fx_surface: pygame.Surface,
        cam_offset: Tuple[int, int],
    ) -> None:
        """Desenha céu, estrelas, serras, bambus e pétalas em parallax."""
        surface.blit(self.sky_surface, (0, 0))  # Desenha o céu pré-renderizado como base

        # Estrelas cintilantes na camada alfa (twinkle sempre positivo evita alpha inválido)
        for star in self.stars:
            twinkle = 0.55 + 0.45 * math.sin(self.elapsed * 2.1 + star["phase"])  # Intervalo [0.10, 1.0]
            alpha = int(clamp(165 * twinkle, 15, 255))  # Garante alfa válido dentro de [15, 255]
            sx = int(star["x"] + cam_offset[0] * 0.1)  # Tremor mínimo por estar muito distante
            sy = int(star["y"] + cam_offset[1] * 0.1)
            pygame.draw.circle(
                fx_surface,
                (*Palette.TEXT_CREAM, alpha),
                (sx, sy),
                int(star["size"]),
            )

        # Desenha cada camada de parallax repetida em loop contínuo (seamless tiling)
        for (layer_surf, layer_w), offset_val, factor in (
            (self.far_mountains, self.far_offset, 0.25),
            (self.mid_mountains, self.mid_offset, 0.45),
            (self.bamboo_layer, self.bamboo_offset, 0.65),
        ):
            lx = -int(offset_val) + int(cam_offset[0] * factor)  # Posição X da cópia principal
            ly = int(cam_offset[1] * factor)  # Posição Y com fração do tremor da câmera
            surface.blit(layer_surf, (lx, ly))  # Desenha cópia principal
            if lx > 0:  # Cobre eventual fresta à esquerda durante tremor forte de câmera
                surface.blit(layer_surf, (lx - layer_w, ly))
            if lx + layer_w < SCREEN_WIDTH:  # Desenha continuação à direita quando o tile termina
                surface.blit(layer_surf, (lx + layer_w, ly))

        # Pétalas flutuantes girando na camada de transparência
        for petal in self.ambient_petals:
            px = petal["x"] + cam_offset[0] * 0.75
            py = petal["y"] + cam_offset[1] * 0.75
            rot = self.elapsed * 2.4 + petal["phase"]  # Ângulo atual da pétala
            s = petal["size"]
            pts = [  # Quatro vértices do losango rotacionado
                (px + math.cos(rot) * s * 1.4, py + math.sin(rot) * s * 1.4),
                (px + math.cos(rot + 1.4) * s * 0.6, py + math.sin(rot + 1.4) * s * 0.6),
                (px - math.cos(rot) * s * 1.4, py - math.sin(rot) * s * 1.4),
                (px + math.cos(rot - 1.4) * s * 0.6, py + math.sin(rot - 1.4) * s * 0.6),
            ]
            pygame.draw.polygon(fx_surface, (*petal["color"], 185), pts)

    def draw_ground(self, surface: pygame.Surface, cam_offset: Tuple[int, int]) -> None:
        """Desenha barranco em tinta sumi-e com pedras e capim ao vento."""
        gy = PLAYABLE_HEIGHT + cam_offset[1]  # Linha do horizonte deslocada pelo tremor vertical
        gx = cam_offset[0]  # Tremor horizontal da câmera

        pygame.draw.rect(  # Retângulo escuro de fundo do chão (com folga nas bordas para o tremor)
            surface,
            Palette.GROUND_INK,
            (-24, gy, SCREEN_WIDTH + 48, GROUND_HEIGHT + 30),
        )
        pygame.draw.line(  # Linha mineral de contorno no topo do solo
            surface,
            Palette.GROUND_RIM,
            (-24, gy),
            (SCREEN_WIDTH + 24, gy),
            3,
        )

        # Traços horizontais repetidos a cada 48 px para transmitir sensação de velocidade no solo
        step = 48
        start_x = -int(self.ground_offset) + gx - step
        for x in range(start_x, SCREEN_WIDTH + step * 2, step):
            pygame.draw.line(surface, Palette.MOUNTAIN_MID, (x + 8, gy + 18), (x + 30, gy + 18), 2)
            pygame.draw.line(surface, Palette.MOUNTAIN_MID, (x + 2, gy + 44), (x + 18, gy + 44), 2)

        # Lâminas de capim balançando organicamente sobre o topo do barranco
        for blade in self.grass_blades:
            bx = int(blade["x"]) + gx
            sway = math.sin(self.elapsed * 3.8 + blade["phase"]) * 6.0 - 4.0  # Inclinação pelo vento
            tip = (bx + sway, gy - blade["height"])  # Ponta da folha
            pygame.draw.polygon(
                surface,
                Palette.GROUND_INK,
                [(bx - 3, gy + 1), tip, (bx + 3, gy + 1)],  # Triângulo fino da folha de capim
            )


# =============================================================================
# OBSTÁCULOS (PORTAIS DO SANTUÁRIO) E LANTERNAS COLETÁVEIS
# =============================================================================

class TempleGate:
    """Portal de templo com cornijas, talismã ao vento e flutuação opcional."""

    def __init__(
        self,
        x: float,
        gap_y: float,
        gap_height: float,
        drift_amp: float = 0.0,
    ) -> None:
        self.x = x  # Posição horizontal da borda esquerda do portal
        self.width = GATE_WIDTH  # Largura do pilar
        self.base_gap_y = gap_y  # Altura central original da passagem
        self.gap_y = gap_y  # Altura central atual (pode oscilar se drift_amp > 0)
        self.gap_height = gap_height  # Espaço livre vertical entre os dois pilares
        self.drift_amp = drift_amp  # Amplitude de oscilação vertical (0 = portal fixo)
        self.drift_phase = random.uniform(0.0, math.tau)  # Fase inicial do movimento vertical
        self.wind_phase = random.uniform(0.0, math.tau)  # Fase inicial do balanço do talismã
        self.scored = False  # Evita pontuar duas vezes no mesmo portal
        self.harmony_flash: float = 0.0  # Intensidade do brilho jade após ser ultrapassado

    @property
    def top_rect(self) -> pygame.Rect:
        """Retângulo de colisão do pilar superior."""
        height = max(0, int(self.gap_y - self.gap_height / 2))  # Vai do topo (0) até o início da janela
        return pygame.Rect(int(self.x), 0, self.width, height)

    @property
    def bottom_rect(self) -> pygame.Rect:
        """Retângulo de colisão do pilar inferior."""
        top_y = int(self.gap_y + self.gap_height / 2)  # Começa abaixo da janela de passagem
        height = max(0, PLAYABLE_HEIGHT - top_y)  # Estende-se exatamente até o chão
        return pygame.Rect(int(self.x), top_y, self.width, height)

    def update(self, dt: float, scroll_speed: float) -> None:
        """Avança o portal e anima vento e oscilação vertical suave."""
        self.x -= scroll_speed * dt  # Desloca portal para a esquerda conforme velocidade do vento
        self.wind_phase += dt * 3.6  # Atualiza ciclo do vento que balança o talismã
        if self.drift_amp > 0.0:  # Portais móveis sobem e descem suavemente em onda senoidal
            self.drift_phase += dt * 1.9
            self.gap_y = self.base_gap_y + math.sin(self.drift_phase) * self.drift_amp

        if self.harmony_flash > 0.0:  # Apaga gradualmente o brilho pós-pontuação
            self.harmony_flash = max(0.0, self.harmony_flash - dt * 2.5)

    def trigger_scored(self, is_clean_center: bool) -> None:
        """Marca passagem pelo portal e ativa brilho jade/ouro."""
        self.scored = True  # Bloqueia contagem repetida
        self.harmony_flash = 1.0 if is_clean_center else 0.55  # Brilho mais intenso se passou no centro

    def is_offscreen(self) -> bool:
        """Retorna True quando o portal já saiu à esquerda."""
        return self.x + self.width < -40  # Margem de 40 px garante que sombras também saíram

    def draw(
        self,
        surface: pygame.Surface,
        fx_surface: pygame.Surface,
        offset: Tuple[int, int],
    ) -> None:
        """Desenha os dois pilares do portal com sombras, cornijas e talismã."""
        ox, oy = offset  # Deslocamento atual do tremor da câmera
        trim_color = Palette.GOLD_FOIL  # Cor padrão do friso da cornija
        if self.harmony_flash > 0.0:  # Mistura ouro com verde jade logo após pontuar
            trim_color = tuple(
                int(lerp(Palette.GOLD_FOIL[i], Palette.JADE_MIST[i], self.harmony_flash))
                for i in range(3)
            )

        self._draw_pillar(surface, fx_surface, self.top_rect, ox, oy, trim_color, is_top=True)
        self._draw_pillar(surface, fx_surface, self.bottom_rect, ox, oy, trim_color, is_top=False)

    def _draw_pillar(
        self,
        surface: pygame.Surface,
        fx_surface: pygame.Surface,
        rect: pygame.Rect,
        ox: int,
        oy: int,
        trim_color: Tuple[int, int, int],
        is_top: bool,
    ) -> None:
        """Renderiza um pilar esculpido com sombra, beiral Torii e talismã."""
        if rect.height <= 0:  # Não tenta desenhar pilar com altura nula
            return

        r = rect.move(ox, oy)  # Aplica o tremor da câmera à posição visual do pilar
        cap_h = 24  # Altura da cornija (topo largo do pilar)
        overhang = 9  # Quanto a cornija sobressai lateralmente além do tronco
        cap_y = r.bottom - cap_h if is_top else r.top  # Fica na ponta voltada para a abertura
        cap_rect = pygame.Rect(r.x - overhang, cap_y, r.width + overhang * 2, cap_h)

        # Sombra projetada suave atrás do tronco e da cornija na camada alfa
        pygame.draw.rect(
            fx_surface,
            (*Palette.INK_SHADOW, 88),
            (r.x + 8, r.y + 8, r.width, r.height),
            border_radius=4,
        )
        pygame.draw.rect(
            fx_surface,
            (*Palette.INK_SHADOW, 105),
            (cap_rect.x + 8, cap_rect.y + 8, cap_rect.width, cap_rect.height),
            border_radius=5,
        )

        # Corpo principal escuro, faixa de chanfro e reflexo quente lateral do pôr do sol
        pygame.draw.rect(surface, Palette.PILLAR_DARK, r, border_radius=3)
        pygame.draw.rect(surface, Palette.PILLAR_MID, (r.x + 7, r.y, 13, r.height))
        pygame.draw.line(surface, Palette.PILLAR_WARM, (r.right - 3, r.top), (r.right - 3, r.bottom), 3)

        # Aura sutil sinalizando portais móveis ou recém-pontuados
        if self.drift_amp > 0.0 or self.harmony_flash > 0.05:
            glow_col = Palette.JADE_MIST if self.harmony_flash > 0.2 else Palette.GOLD_FOIL
            glow = get_glow_surface(30, glow_col, max_alpha=68)
            fx_surface.blit(
                glow,
                (
                    cap_rect.centerx - glow.get_width() // 2,
                    cap_rect.centery - glow.get_height() // 2,
                ),
            )

        # Cornija em estilo Torii com duas pontas triangulares levemente arrebitadas
        pygame.draw.rect(surface, Palette.PILLAR_MID, cap_rect, border_radius=4)
        eave_y = cap_rect.bottom if is_top else cap_rect.top
        eave_dir = -1 if is_top else 1  # Orienta os chifres para cima no topo e para baixo na base
        wing_left = [
            (cap_rect.left, eave_y),
            (cap_rect.left - 8, eave_y + 7 * eave_dir),
            (cap_rect.left + 12, eave_y + 10 * eave_dir),
        ]
        wing_right = [
            (cap_rect.right, eave_y),
            (cap_rect.right + 8, eave_y + 7 * eave_dir),
            (cap_rect.right - 12, eave_y + 10 * eave_dir),
        ]
        pygame.draw.polygon(surface, Palette.PILLAR_DARK, wing_left)
        pygame.draw.polygon(surface, Palette.PILLAR_DARK, wing_right)

        # Friso luminoso dourado/jade ao longo da cornija
        line_y = cap_rect.bottom - 7 if is_top else cap_rect.top + 6
        pygame.draw.line(
            surface,
            trim_color,
            (cap_rect.left + 6, line_y),
            (cap_rect.right - 6, line_y),
            2,
        )

        # Talismã de papel (ofuda) pendurado sob o pilar superior balançando com o vento
        if is_top and r.height > 32:
            sway = math.sin(self.wind_phase) * 7.0 - 4.0  # Inclinação horizontal da ponta solta
            anchor_x = cap_rect.centerx - 16
            anchor_y = cap_rect.bottom - 1
            ofuda = [
                (anchor_x - 4, anchor_y),
                (anchor_x + 4, anchor_y),
                (anchor_x + 4 + sway, anchor_y + 22),
                (anchor_x - 4 + sway, anchor_y + 22),
            ]
            pygame.draw.polygon(surface, Palette.OFUDA_PAPER, ofuda)
            pygame.draw.circle(
                surface,
                Palette.OFUDA_SEAL,
                (int(anchor_x + sway * 0.45), int(anchor_y + 9)),
                2,
            )


class LanternOrb:
    """Lanterna de papel flutuante coletável que concede bônus e estende a harmonia."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x  # Posição X atual
        self.base_y = y  # Altura central ao redor da qual a lanterna flutua
        self.y = y  # Posição Y atual
        self.radius = 12.0  # Raio usado para detectar coleta
        self.phase = random.uniform(0.0, math.tau)  # Fase aleatória da flutuação
        self.collected = False  # Marca se já foi pega pelo tsuru

    def update(self, dt: float, scroll_speed: float) -> None:
        """Desloca a lanterna com leve flutuação vertical."""
        self.x -= scroll_speed * dt  # Acompanha a velocidade do cenário
        self.phase += dt * 3.8  # Avança ciclo senoidal de flutuação
        self.y = self.base_y + math.sin(self.phase) * 9.0  # Sobe e desce 9 pixels suavemente

    def is_offscreen(self) -> bool:
        """Retorna True se saiu da tela ou já foi coletada."""
        return self.collected or self.x < -30  # Remove se já coletada ou fora da borda esquerda

    def draw(
        self,
        surface: pygame.Surface,
        fx_surface: pygame.Surface,
        offset: Tuple[int, int],
    ) -> None:
        """Desenha lanterna facetada com aura âmbar acolhedora."""
        px = int(self.x + offset[0])
        py = int(self.y + offset[1])

        glow = get_glow_surface(36, Palette.GOLD_FOIL, max_alpha=120)  # Aura dourada ao redor
        fx_surface.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))

        pygame.draw.circle(fx_surface, (*Palette.INK_SHADOW, 80), (px + 4, py + 6), 11)  # Sombra suave

        # Corpo externo dourado + núcleo aceso creme + tampas escuras nas extremidades
        diamond = [(px, py - 13), (px + 10, py), (px, py + 13), (px - 10, py)]
        pygame.draw.polygon(surface, Palette.GOLD_FOIL, diamond)
        inner = [(px, py - 8), (px + 5, py), (px, py + 8), (px - 5, py)]
        pygame.draw.polygon(surface, Palette.SUN_CORE, inner)
        pygame.draw.line(surface, Palette.PILLAR_DARK, (px - 6, py - 13), (px + 6, py - 13), 2)
        pygame.draw.line(surface, Palette.PILLAR_DARK, (px - 6, py + 13), (px + 6, py + 13), 2)


# =============================================================================
# JOGADOR: TSURU DE ORIGAMI ARTICULADO EM 2.5D
# =============================================================================

class OrigamiCrane:
    """Pássaro de papel dobrado com asas articuladas, inércia e fita de seda contínua."""

    def __init__(self, x: float, y: float) -> None:
        self.start_x = x  # Posição horizontal fixa de referência para reinícios
        self.start_y = y  # Altura inicial ao começar ou voltar ao menu
        self.x = x  # Posição horizontal atual
        self.y = y  # Posição vertical atual
        self.vy: float = 0.0  # Velocidade vertical atual (negativa = subindo)
        self.radius: float = 15.0  # Raio aproximado do corpo para colisão e solo
        self.angle: float = 0.0  # Ângulo de inclinação em graus (+ nariz para cima)
        self.wing_phase: float = 0.0  # Ângulo da animação senoidal das asas
        self.squash_x: float = 1.0  # Escala horizontal (usada para efeito Squash & Stretch)
        self.squash_y: float = 1.0  # Escala vertical (estica ao pular e volta a 1.0)
        self.ribbon_points: List[Tuple[float, float, float]] = []  # Lista (x, y, vida) da fita
        self._ribbon_timer: float = 0.0  # Temporizador para adicionar novos nós à fita
        self._demo_cooldown: float = 0.0  # Intervalo mínimo entre pulos da IA no MENU

    def reset(self) -> None:
        """Reinicia posição, ângulo, escala e rastro."""
        self.x = self.start_x
        self.y = self.start_y
        self.vy = 0.0
        self.angle = 0.0
        self.wing_phase = 0.0
        self.squash_x = 1.0
        self.squash_y = 1.0
        self.ribbon_points.clear()  # Apaga fita da tentativa anterior
        self._ribbon_timer = 0.0
        self._demo_cooldown = 0.0

    def jump(self) -> None:
        """Impulso vertical com alongamento sutil de papel e batida de asa."""
        self.vy = JUMP_VELOCITY  # Aplica impulso instantâneo para cima
        self.squash_x = 0.84  # Comprime ligeiramente na largura
        self.squash_y = 1.20  # Estica na altura para dar sensação elástica de salto
        self.wing_phase = 0.25  # Sincroniza o início da batida de asa com o pulo

    def update_demo(self, dt: float, gates: List[TempleGate]) -> bool:
        """Piloto automático fluido para a demonstração na tela inicial."""
        self._demo_cooldown = max(0.0, self._demo_cooldown - dt)  # Conta regressiva entre batidas
        target_y = PLAYABLE_HEIGHT * 0.48  # Altura padrão caso não haja portal próximo

        upcoming = [g for g in gates if g.x + g.width >= self.x - 10]  # Filtra portais ainda à frente
        if upcoming:
            nearest = min(upcoming, key=lambda g: g.x)  # Seleciona o portal mais próximo
            target_y = nearest.gap_y + 8.0  # Mira ligeiramente abaixo do centro para pular suave

        jumped = False
        # Bate asas se estiver abaixo da altura alvo (sem já estar subindo rápido) ou perto do chão
        if (self.y > target_y and self.vy > -35.0 and self._demo_cooldown <= 0.0) or (
            self.y > PLAYABLE_HEIGHT - 84
        ):
            self.jump()
            self._demo_cooldown = 0.22  # Evita múltiplos pulos seguidos em quadros consecutivos
            jumped = True

        self.update(dt)  # Executa a física normal do tsuru
        return jumped  # Retorna se pulou neste quadro para emitir partículas de asa

    def update(self, dt: float) -> None:
        """Atualiza gravidade, inclinação interpolada, asas e fita de seda."""
        self.vy = min(MAX_FALL_SPEED, self.vy + GRAVITY * dt)  # Acelera queda até velocidade máxima
        self.y += self.vy * dt  # Atualiza posição vertical baseada em Delta Time
        self.y = max(self.radius + 6.0, self.y)  # Impede o tsuru de sair pelo teto da janela

        if self.vy < 0:  # Subindo: inclina o bico para cima (+24 graus)
            target_angle = 24.0
        else:  # Caindo: mapeia suavemente de +16° até -72° conforme ganha velocidade de queda
            fall_ratio = clamp(self.vy / MAX_FALL_SPEED, 0.0, 1.0)
            target_angle = lerp(16.0, -72.0, fall_ratio ** 1.3)

        self.angle = lerp(self.angle, target_angle, min(1.0, dt * 10.0))  # Suaviza rotação
        self.squash_x = lerp(self.squash_x, 1.0, min(1.0, dt * 12.0))  # Restaura largura normal
        self.squash_y = lerp(self.squash_y, 1.0, min(1.0, dt * 12.0))  # Restaura altura normal

        flap_speed = 16.5 if self.vy < 45 else 7.8  # Bate asas rápido na subida, mais lento ao planar
        self.wing_phase += dt * flap_speed

        # Cria um novo ponto da fita atrás da cauda a cada ~22 milissegundos
        self._ribbon_timer += dt
        if self._ribbon_timer >= 0.022:
            self._ribbon_timer = 0.0
            rad = math.radians(-self.angle)  # Converte inclinação atual para radianos
            tail_x = self.x - math.cos(rad) * 18.0  # Calcula ponta exata da cauda rotacionada
            tail_y = self.y - math.sin(rad) * 18.0
            self.ribbon_points.append((tail_x, tail_y, 1.0))  # Vida inicial = 1.0

        next_ribbon: List[Tuple[float, float, float]] = []
        for rx, ry, life in self.ribbon_points:
            new_life = life - dt * 2.9  # Reduz vida da cauda continuamente
            if new_life > 0.0:  # Desloca pontos para trás simulando o vento relativo
                next_ribbon.append((rx - 155.0 * dt, ry, new_life))
        self.ribbon_points = next_ribbon

    def get_hitbox(self) -> pygame.Rect:
        """Retorna caixa de colisão justa e precisa ao núcleo do tsuru."""
        size = int((self.radius - 4) * 2)  # Hitbox 4 px menor que as pontas para ser justa
        return pygame.Rect(
            int(self.x - size // 2),
            int(self.y - size // 2),
            size,
            size,
        )

    def _draw_ribbon(
        self,
        fx_surface: pygame.Surface,
        offset: Tuple[int, int],
    ) -> None:
        """Desenha uma fita cônica translúcida que acompanha a trajetória."""
        if len(self.ribbon_points) < 2:  # Precisa de pelo menos 2 pontos para formar um segmento
            return
        ox, oy = offset
        for i in range(len(self.ribbon_points) - 1):
            x1, y1, l1 = self.ribbon_points[i]
            x2, y2, l2 = self.ribbon_points[i + 1]
            alpha = int(130 * min(l1, l2))  # Transparência acompanha o ponto mais antigo
            if alpha <= 2:
                continue
            w1 = max(1.0, 5.5 * l1)  # Largura da fita afina até a ponta final
            w2 = max(1.0, 5.5 * l2)
            quad = [  # Trapézio conectando os dois pontos consecutivos da fita
                (x1 + ox, y1 + oy - w1),
                (x2 + ox, y2 + oy - w2),
                (x2 + ox, y2 + oy + w2),
                (x1 + ox, y1 + oy + w1),
            ]
            pygame.draw.polygon(fx_surface, (*Palette.RIBBON_SILK, alpha), quad)

    def draw(
        self,
        surface: pygame.Surface,
        fx_surface: pygame.Surface,
        offset: Tuple[int, int],
    ) -> None:
        """Renderiza fita, aura quente, sombra e dobras articuladas de origami."""
        self._draw_ribbon(fx_surface, offset)  # Desenha primeiro a fita de seda atrás do tsuru

        ox, oy = offset
        glow = get_glow_surface(42, Palette.GOLD_FOIL, max_alpha=95)  # Aura dourada envolvente
        fx_surface.blit(
            glow,
            (int(self.x + ox) - glow.get_width() // 2, int(self.y + oy) - glow.get_height() // 2),
        )

        # Cria tela local transparente onde o origami é montado antes de deformar e girar
        canvas_size = 86
        crane_surf = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        cx, cy = canvas_size // 2, canvas_size // 2

        wing_lift = math.sin(self.wing_phase)  # Oscila entre -1 (asa baixa) e +1 (asa alta)
        wing_tip_x = cx - 4 + wing_lift * 2.5
        wing_tip_y = cy - wing_lift * 23.0 - 2.0  # Move ponta da asa para cima ou para baixo
        wing_color = Palette.PAPER_LIGHT if wing_lift >= 0 else Palette.PAPER_SHADOW

        wing_poly = [(cx - 8, cy + 1), (cx + 7, cy - 1), (wing_tip_x, wing_tip_y)]
        wing_trim = [
            (cx - 3, cy),
            (cx + 6, cy - 1),
            (wing_tip_x + 2, wing_tip_y + (3 if wing_lift >= 0 else -3)),
        ]
        if wing_lift >= 0:  # Quando a asa sobe, fica atrás do corpo em perspectiva 2.5D
            pygame.draw.polygon(crane_surf, wing_color, wing_poly)
            pygame.draw.polygon(crane_surf, Palette.WING_ACCENT, wing_trim, 2)

        # Cauda dobrada à esquerda
        tail_poly = [(cx - 22, cy - 7), (cx - 8, cy - 1), (cx - 12, cy + 5)]
        pygame.draw.polygon(crane_surf, Palette.PAPER_MID, tail_poly)

        # Corpo em duas facetas de papel (inferior sombreada e superior iluminada)
        body_lower = [(cx - 14, cy + 3), (cx + 2, cy - 2), (cx + 12, cy + 4), (cx - 3, cy + 8)]
        body_upper = [(cx - 16, cy), (cx + 4, cy - 6), (cx + 13, cy + 1), (cx + 1, cy + 3)]
        pygame.draw.polygon(crane_surf, Palette.PAPER_SHADOW, body_lower)
        pygame.draw.polygon(crane_surf, Palette.PAPER_LIGHT, body_upper)

        # Pescoço inclinado, cabeça com olho lacre e bico dourado
        neck_poly = [(cx + 6, cy - 2), (cx + 15, cy - 13), (cx + 19, cy - 10), (cx + 12, cy + 2)]
        pygame.draw.polygon(crane_surf, Palette.PAPER_MID, neck_poly)

        beak_poly = [(cx + 14, cy - 13), (cx + 26, cy - 8), (cx + 16, cy - 7)]
        pygame.draw.polygon(crane_surf, Palette.GOLD_FOIL, beak_poly)
        pygame.draw.circle(crane_surf, Palette.WING_ACCENT, (cx + 16, cy - 10), 2)

        if wing_lift < 0:  # Quando a asa desce, passa na frente do corpo cobrindo-o parcialmente
            pygame.draw.polygon(crane_surf, Palette.PAPER_MID, wing_poly)
            pygame.draw.polygon(crane_surf, Palette.WING_ACCENT, wing_trim, 2)

        # Aplica deformação Squash & Stretch e em seguida rotaciona pela inclinação
        scaled_w = max(8, int(canvas_size * self.squash_x))
        scaled_h = max(8, int(canvas_size * self.squash_y))
        deformed = pygame.transform.smoothscale(crane_surf, (scaled_w, scaled_h))
        rotated = pygame.transform.rotate(deformed, self.angle)

        # Cria uma silhueta escura translúcida do tsuru como sombra projetada
        shadow_surf = rotated.copy()
        shadow_surf.fill((*Palette.INK_SHADOW, 115), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(
            shadow_surf,
            shadow_surf.get_rect(center=(int(self.x + ox + 5), int(self.y + oy + 8))),
        )
        surface.blit(
            rotated,
            rotated.get_rect(center=(int(self.x + ox), int(self.y + oy))),
        )


# =============================================================================
# BOTÃO EDITORIAL DE INTERFACE
# =============================================================================

class Button:
    """Botão minimalista com moldura dupla, sombra e resposta suave ao cursor."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        accent_color: Tuple[int, int, int] = Palette.GOLD_FOIL,
    ) -> None:
        self.base_rect = rect.copy()  # Área de clique e tamanho em repouso
        self.text = text  # Rótulo central do botão
        self.font = font  # Fonte usada para desenhar o rótulo
        self.accent_color = accent_color  # Cor da borda e do realce no hover
        self.hover_progress: float = 0.0  # Progresso animado [0, 1] quando o cursor está em cima
        self.is_hovered: bool = False  # Estado booleano de sobreposição do mouse

    def update(self, dt: float, mouse_pos: Tuple[int, int]) -> None:
        """Interpola animação de destaque ao passar o mouse."""
        self.is_hovered = self.base_rect.collidepoint(mouse_pos)  # Checa se cursor está dentro
        target = 1.0 if self.is_hovered else 0.0  # Alvo de animação (1 = destacado, 0 = normal)
        self.hover_progress = lerp(self.hover_progress, target, min(1.0, dt * 13.0))

    def is_clicked(self, event: pygame.event.Event) -> bool:
        """Detecta clique esquerdo válido dentro da área do botão."""
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1  # Botão 1 = clique esquerdo
            and self.base_rect.collidepoint(event.pos)
        )

    def draw(self, surface: pygame.Surface, y_offset: int = 0, alpha: int = 255) -> None:
        """Desenha o botão com sombra projetada e filete interno dourado."""
        expand = int(4 * self.hover_progress)  # Cresce até 4 px para cada lado no hover
        rect = pygame.Rect(
            self.base_rect.x - expand,
            self.base_rect.y + y_offset - expand // 2,
            self.base_rect.width + expand * 2,
            self.base_rect.height + expand,
        )

        # Sombra projetada deslocada abaixo do botão
        shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(
            shadow,
            (*Palette.INK_SHADOW, int(135 * (alpha / 255.0))),
            (0, 0, rect.width, rect.height),
            border_radius=10,
        )
        surface.blit(shadow, (rect.x + 3, rect.y + 5))

        # Mistura cor de fundo do cartão com a cor de destaque proporcionalmente ao hover
        fill = tuple(
            int(lerp(Palette.CARD_BG[i], self.accent_color[i], 0.14 + 0.18 * self.hover_progress))
            for i in range(3)
        )
        btn = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(btn, (*fill, alpha), (0, 0, rect.width, rect.height), border_radius=10)
        pygame.draw.rect(
            btn,
            (*self.accent_color, alpha),
            (0, 0, rect.width, rect.height),
            width=2,  # Moldura externa
            border_radius=10,
        )
        pygame.draw.rect(
            btn,
            (*self.accent_color, int(alpha * 0.45)),
            (4, 4, rect.width - 8, rect.height - 8),
            width=1,  # Filete interno fino (estilo artesanal)
            border_radius=7,
        )
        surface.blit(btn, rect.topleft)

        draw_text_with_shadow(
            surface,
            self.font,
            self.text,
            Palette.TEXT_CREAM,
            rect.center,
            shadow_offset=(1, 2),
            alpha=alpha,
        )


# =============================================================================
# ORQUESTRADOR PRINCIPAL DO JOGO
# =============================================================================

class Game:
    """Gerencia máquina de estados, loop a 60 FPS, pontuação e interface."""

    def __init__(self) -> None:
        pygame.init()  # Inicializa módulos internos do Pygame (vídeo, fontes, eventos)
        pygame.display.set_caption("TSURU — Ventos do Crepúsculo")  # Título da janela
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))  # Cria tela principal
        self.fx_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)  # Camada alfa única
        self.clock = pygame.time.Clock()  # Relógio para controle preciso de FPS e Delta Time
        self.running = True  # Flag que mantém o loop principal rodando

        self.sound = SoundManager()  # Gerenciador de síntese sonora procedural
        self.highscore_manager = HighScoreManager()  # Gerenciador de recordes em JSON
        self.camera_shake = CameraShake()  # Sistema de tremor de câmera
        self.world = ParallaxWorld()  # Cenário em camadas parallax
        self.player = OrigamiCrane(x=140.0, y=PLAYABLE_HEIGHT * 0.46)  # Personagem tsuru

        self.gates: List[TempleGate] = []  # Lista de portais ativos em tela
        self.lanterns: List[LanternOrb] = []  # Lista de lanternas coletáveis ativas
        self.particles: List[Particle] = []  # Lista de partículas de efeitos
        self.shockwaves: List[Shockwave] = []  # Lista de ondas expansivas
        self.floating_texts: List[FloatingText] = []  # Lista de textos flutuantes

        self.state: GameState = GameState.MENU  # Inicia sempre na tela de menu
        self.score: int = 0  # Pontuação da partida atual
        self.harmony_streak: int = 0  # Sequência atual de passagens limpas / lanternas
        self.max_streak_run: int = 0  # Maior sequência obtida nesta tentativa
        self.is_new_record: bool = False  # Indica se o recorde foi batido ao morrer
        self.spawn_timer: float = 0.0  # Cronômetro regressivo para criar o próximo portal
        self.ui_time: float = 0.0  # Tempo contínuo para animações pulsantes da interface
        self.game_over_timer: float = 0.0  # Tempo decorrido desde a colisão (para transição suave)
        self.flash_alpha: float = 0.0  # Opacidade atual do flash de tela
        self.flash_color: Tuple[int, int, int] = Palette.SUN_CORE  # Cor do flash de tela
        self.score_pop_scale: float = 1.0  # Escala animada do placar ao ganhar pontos

        self._init_fonts()  # Carrega as fontes tipográficas
        self._init_buttons()  # Cria botões clicáveis da interface
        self._seed_demo_gates()  # Coloca portais iniciais para o voo automático do MENU

    def _init_fonts(self) -> None:
        """Combina tipografia serifada para títulos e sans-serif limpa para HUD."""
        self.font_title = pygame.font.SysFont("georgia,palatino,serif", 56, bold=True)
        self.font_heading = pygame.font.SysFont("georgia,palatino,serif", 32, bold=True)
        self.font_score = pygame.font.SysFont("georgia,palatino,serif", 52, bold=True)
        self.font_button = pygame.font.SysFont("calibri,trebuchetms,sans-serif", 21, bold=True)
        self.font_body = pygame.font.SysFont("calibri,trebuchetms,sans-serif", 18, bold=False)
        self.font_small = pygame.font.SysFont("calibri,trebuchetms,sans-serif", 14, bold=True)

    def _init_buttons(self) -> None:
        """Posiciona os botões dos painéis de Pausa e Game Over."""
        cx = SCREEN_WIDTH // 2  # Eixo central horizontal da janela
        self.btn_resume = Button(
            pygame.Rect(cx - 115, 344, 230, 48), "CONTINUAR", self.font_button, Palette.JADE_MIST
        )
        self.btn_pause_restart = Button(
            pygame.Rect(cx - 115, 406, 230, 48), "REINICIAR", self.font_button, Palette.GOLD_FOIL
        )
        self.btn_pause_menu = Button(
            pygame.Rect(cx - 115, 468, 230, 48),
            "MENU INICIAL",
            self.font_button,
            Palette.TEXT_MUTED,
        )
        self.btn_restart = Button(
            pygame.Rect(cx - 125, 476, 250, 52),
            "VOAR NOVAMENTE",
            self.font_button,
            Palette.GOLD_FOIL,
        )
        self.btn_gameover_menu = Button(
            pygame.Rect(cx - 125, 540, 250, 42),
            "VOLTAR AO MENU",
            self.font_small,
            Palette.TEXT_MUTED,
        )
        self.mute_rect = pygame.Rect(SCREEN_WIDTH - 52, 16, 36, 36)  # Área clicável do botão de som

    def _seed_demo_gates(self) -> None:
        """Inicializa dois portais iniciais para a demonstração viva do menu."""
        self.gates.clear()
        self.lanterns.clear()
        for idx in range(2):
            gx = SCREEN_WIDTH + 90 + idx * 280
            gap_y = random.uniform(205.0, PLAYABLE_HEIGHT - 205.0)
            self.gates.append(TempleGate(gx, gap_y, BASE_GATE_GAP + 12))

    def _current_scroll_speed(self) -> float:
        """Aumenta gradualmente a velocidade do vento com o progresso do jogador."""
        if self.state == GameState.MENU:
            return BASE_SCROLL_SPEED * 0.90  # Menu um pouco mais sereno e contemplativo
        bonus = min(MAX_SCROLL_SPEED - BASE_SCROLL_SPEED, self.score * 2.1)  # Acelera +2.1 por ponto
        return BASE_SCROLL_SPEED + bonus

    def _current_gate_gap(self) -> float:
        """Ajusta a abertura dos portais de maneira suave e justa."""
        reduction = min(BASE_GATE_GAP - MIN_GATE_GAP, self.score * 0.78)  # Fecha aos poucos até o mínimo
        return BASE_GATE_GAP - reduction

    def _spawn_gate(self) -> None:
        """Gera um novo portal (com possível flutuação após 7 pontos) e lanterna."""
        gap = self._current_gate_gap()
        margin = 98 + gap / 2  # Margem superior/inferior para o vão nunca encostar no chão ou teto
        gap_y = random.uniform(margin, PLAYABLE_HEIGHT - margin)

        drift = 0.0  # Por padrão o portal é fixo
        if self.state == GameState.JOGANDO and self.score >= 7 and random.random() < 0.35:
            drift = random.uniform(16.0, 28.0)  # A partir de 7 pontos, 35% dos portais oscilam

        gate_x = SCREEN_WIDTH + 34  # Nasce ligeiramente fora da borda direita
        self.gates.append(TempleGate(gate_x, gap_y, gap, drift_amp=drift))

        # 42% de chance de surgir uma lanterna dourada no vão entre este portal e o próximo
        if self.state == GameState.JOGANDO and random.random() < 0.42:
            lantern_y = clamp(
                gap_y + random.uniform(-55.0, 55.0),  # Varia altura próxima à saída do portal
                95.0,
                PLAYABLE_HEIGHT - 95.0,
            )
            self.lanterns.append(LanternOrb(gate_x + 150.0, lantern_y))

    def _emit_wing_particles(self) -> None:
        """Solta pequenas pétalas e brilhos de papel ao bater asas."""
        for _ in range(7):
            angle = random.uniform(math.pi * 0.7, math.pi * 1.35)  # Direciona partículas para trás
            speed = random.uniform(65.0, 155.0)
            kind = "petal" if random.random() < 0.55 else "ember"
            color = (
                random.choice([Palette.PETAL_ROSE, Palette.PAPER_LIGHT])
                if kind == "petal"
                else Palette.GOLD_FOIL
            )
            self.particles.append(
                Particle(
                    x=self.player.x - 10,
                    y=self.player.y + 4,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed + 30.0,
                    color=color,
                    size=random.uniform(3.2, 5.2),
                    lifetime=random.uniform(0.35, 0.62),
                    gravity=120.0 if kind == "petal" else 220.0,
                    kind=kind,
                )
            )
        self.shockwaves.append(  # Pequena onda de ar deslocado sob as asas
            Shockwave(
                self.player.x - 4,
                self.player.y + 4,
                Palette.PAPER_LIGHT,
                max_radius=28.0,
                duration=0.22,
                width=2,
            )
        )

    def _emit_gate_particles(self, is_clean_center: bool) -> None:
        """Emite pétalas e brilhos ao cruzar um portal em harmonia."""
        count = 16 if is_clean_center else 8  # Passagem central gera o dobro de partículas
        for _ in range(count):
            angle = random.uniform(0.0, math.tau)  # Espalha em 360 graus
            speed = random.uniform(75.0, 210.0)
            kind = "petal" if random.random() < 0.6 else "ember"
            color = (
                random.choice([Palette.PETAL_ROSE, Palette.PETAL_GOLD])
                if kind == "petal"
                else Palette.JADE_MIST
            )
            self.particles.append(
                Particle(
                    x=self.player.x + 8,
                    y=self.player.y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=color,
                    size=random.uniform(3.4, 5.6),
                    lifetime=random.uniform(0.45, 0.85),
                    gravity=95.0 if kind == "petal" else 160.0,
                    kind=kind,
                )
            )

        if is_clean_center:  # Onda jade e texto de combo apenas ao passar limpo no centro
            self.shockwaves.append(
                Shockwave(
                    self.player.x,
                    self.player.y,
                    Palette.JADE_MIST,
                    max_radius=54.0,
                    duration=0.35,
                    width=2,
                )
            )
            label = f"HARMONIA x{self.harmony_streak}" if self.harmony_streak > 1 else "+1"
            self.floating_texts.append(
                FloatingText(
                    self.player.x,
                    self.player.y - 26,
                    label,
                    Palette.JADE_MIST if self.harmony_streak > 1 else Palette.TEXT_CREAM,
                    self.font_small,
                )
            )

    def _emit_lantern_particles(self, lx: float, ly: float) -> None:
        """Explosão acolhedora de brasas douradas ao coletar uma lanterna."""
        for _ in range(20):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(95.0, 240.0)
            self.particles.append(
                Particle(
                    x=lx,
                    y=ly,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=random.choice([Palette.GOLD_FOIL, Palette.SUN_CORE, Palette.PETAL_ROSE]),
                    size=random.uniform(3.0, 5.5),
                    lifetime=random.uniform(0.42, 0.78),
                    gravity=140.0,
                    kind="ember",
                )
            )
        self.shockwaves.append(
            Shockwave(lx, ly, Palette.GOLD_FOIL, max_radius=62.0, duration=0.36, width=3)
        )
        self.floating_texts.append(
            FloatingText(lx, ly - 18, "+2 LANTERNA", Palette.GOLD_FOIL, self.font_small)
        )

    def _emit_crash_particles(self) -> None:
        """Dispersão dramática de pétalas e fragmentos de papel na colisão."""
        for _ in range(36):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(110.0, 360.0)
            kind = "petal" if random.random() < 0.65 else "ember"
            color = random.choice(
                [Palette.PAPER_LIGHT, Palette.WING_ACCENT, Palette.GOLD_FOIL, Palette.PETAL_ROSE]
            )
            self.particles.append(
                Particle(
                    x=self.player.x,
                    y=self.player.y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 50.0,  # Impulso inicial leve para cima
                    color=color,
                    size=random.uniform(3.8, 7.0),
                    lifetime=random.uniform(0.55, 1.05),
                    gravity=260.0 if kind == "petal" else 420.0,
                    kind=kind,
                )
            )
        self.shockwaves.append(
            Shockwave(
                self.player.x,
                self.player.y,
                Palette.WING_ACCENT,
                max_radius=96.0,
                duration=0.42,
                width=3,
            )
        )

    def _start_new_game(self) -> None:
        """Inicia uma nova jornada resetando entidades e contadores."""
        self.state = GameState.JOGANDO
        self.score = 0
        self.harmony_streak = 0
        self.max_streak_run = 0
        self.is_new_record = False
        self.score_pop_scale = 1.0
        self.gates.clear()
        self.lanterns.clear()
        self.particles.clear()
        self.shockwaves.clear()
        self.floating_texts.clear()
        self.player.reset()
        self.player.jump()  # Primeiro salto imediato ao iniciar a partida
        self._emit_wing_particles()
        self.spawn_timer = 0.7  # Dá 0.7s de folga antes de surgir o primeiro portal
        self.sound.play("wing")

    def _go_to_menu(self) -> None:
        """Retorna à tela inicial com voo demonstrativo ativo."""
        self.state = GameState.MENU
        self.score = 0
        self.harmony_streak = 0
        self.is_new_record = False
        self.player.reset()
        self.particles.clear()
        self.shockwaves.clear()
        self.floating_texts.clear()
        self._seed_demo_gates()  # Recria portais para a demonstração automática
        self.spawn_timer = 0.25

    def _trigger_game_over(self) -> None:
        """Executa impacto visual/sonoro e muda para GAME_OVER."""
        self.state = GameState.GAME_OVER
        self.game_over_timer = 0.0  # Inicia cronômetro da animação do cartão
        self.is_new_record = self.highscore_manager.update(self.score, self.max_streak_run)
        self.camera_shake.add_trauma(0.82)  # Tremor intenso de impacto
        self.flash_color = Palette.WING_ACCENT  # Flash coral avermelhado
        self.flash_alpha = 125.0
        self._emit_crash_particles()
        self.sound.play("hit")

    def _handle_events(self) -> None:
        """Processa entradas de teclado e mouse conforme o estado ativo."""
        for event in pygame.event.get():  # Consome toda a fila de eventos do quadro
            if event.type == pygame.QUIT:  # Fechamento pelo X da janela
                self.running = False
                return

            if event.type == pygame.KEYDOWN and event.key == pygame.K_m:  # Atalho M alterna áudio
                self.sound.toggle_mute()
                self.sound.play("click")
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.mute_rect.collidepoint(event.pos):  # Clique no ícone de alto-falante
                    self.sound.toggle_mute()
                    self.sound.play("click")
                    continue

            if self.state == GameState.MENU:
                start_key = event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_SPACE,
                    pygame.K_UP,
                    pygame.K_RETURN,
                )
                start_click = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                if start_key or start_click:  # Qualquer tecla de ação ou clique inicia o jogo
                    self._start_new_game()

            elif self.state == GameState.JOGANDO:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        self.player.jump()
                        self._emit_wing_particles()
                        self.sound.play("wing")
                    elif event.key in (pygame.K_p, pygame.K_ESCAPE):  # P ou ESC pausa a partida
                        self.state = GameState.PAUSADO
                        self.sound.play("click")
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.player.jump()
                    self._emit_wing_particles()
                    self.sound.play("wing")

            elif self.state == GameState.PAUSADO:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_SPACE):
                        self.state = GameState.JOGANDO  # Retoma partida
                        self.sound.play("click")
                    elif event.key == pygame.K_r:  # Reinício rápido durante a pausa
                        self.sound.play("click")
                        self._start_new_game()
                elif self.btn_resume.is_clicked(event):
                    self.sound.play("click")
                    self.state = GameState.JOGANDO
                elif self.btn_pause_restart.is_clicked(event):
                    self.sound.play("click")
                    self._start_new_game()
                elif self.btn_pause_menu.is_clicked(event):
                    self.sound.play("click")
                    self._go_to_menu()

            elif self.state == GameState.GAME_OVER:
                ready = self.game_over_timer >= 0.42  # Aguarda transição terminar (evita clique acidental)
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_r, pygame.K_RETURN) and ready:
                        self.sound.play("click")
                        self._start_new_game()
                    elif event.key == pygame.K_ESCAPE:
                        self.sound.play("click")
                        self._go_to_menu()
                elif ready and self.btn_restart.is_clicked(event):
                    self.sound.play("click")
                    self._start_new_game()
                elif ready and self.btn_gameover_menu.is_clicked(event):
                    self.sound.play("click")
                    self._go_to_menu()

    def _update(self, dt: float) -> None:
        """Atualiza física, obstáculos, partículas e animações de UI."""
        self.ui_time += dt  # Avança tempo global das animações de interface
        self.camera_shake.update(dt)  # Decai tremor da câmera
        mouse_pos = pygame.mouse.get_pos()  # Captura posição atual do cursor para botões

        if self.flash_alpha > 0.0:  # Reduz flash de tela até sumir
            self.flash_alpha = max(0.0, self.flash_alpha - dt * 320.0)
        self.score_pop_scale = lerp(self.score_pop_scale, 1.0, min(1.0, dt * 11.0))  # Volta escala a 1.0

        if self.state == GameState.MENU:
            speed = self._current_scroll_speed()
            self.world.update(dt, speed)
            self._update_gates(dt, speed, is_demo=True)
            if self.player.update_demo(dt, self.gates):  # IA pilota o tsuru no menu
                self._emit_wing_particles()
            self._update_vfx(dt)

        elif self.state == GameState.JOGANDO:
            speed = self._current_scroll_speed()
            self.world.update(dt, speed)
            self.player.update(dt)
            self._update_gates(dt, speed, is_demo=False)
            self._update_lanterns(dt, speed)
            self._update_vfx(dt)
            self._check_collisions()

        elif self.state == GameState.PAUSADO:  # Mundo congela; apenas botões respondem ao mouse
            self.btn_resume.update(dt, mouse_pos)
            self.btn_pause_restart.update(dt, mouse_pos)
            self.btn_pause_menu.update(dt, mouse_pos)

        elif self.state == GameState.GAME_OVER:
            self.game_over_timer += dt
            self.btn_restart.update(dt, mouse_pos)
            self.btn_gameover_menu.update(dt, mouse_pos)

            # Se morreu no ar, o tsuru cai até repousar sobre o solo
            if self.player.y + self.player.radius < PLAYABLE_HEIGHT:
                self.player.vy = min(MAX_FALL_SPEED, self.player.vy + GRAVITY * dt)
                self.player.y = min(
                    PLAYABLE_HEIGHT - self.player.radius,
                    self.player.y + self.player.vy * dt,
                )
                self.player.angle = lerp(self.player.angle, -82.0, min(1.0, dt * 10.0))
            self._update_vfx(dt)

    def _update_gates(self, dt: float, speed: float, is_demo: bool) -> None:
        """Gera e movimenta os portais, avaliando passagem e precisão."""
        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0:
            self._spawn_gate()
            interval = GATE_SPAWN_INTERVAL * (BASE_SCROLL_SPEED / max(1.0, speed))  # Mantém distância
            self.spawn_timer = max(1.08, interval)

        for gate in self.gates:
            gate.update(dt, speed)
            # Pontua quando o centro do portal cruza a posição X do tsuru
            if not is_demo and not gate.scored and gate.x + gate.width * 0.5 < self.player.x:
                clean_center = abs(self.player.y - gate.gap_y) <= gate.gap_height * 0.24
                if clean_center:  # Passou dentro da faixa central (48% centrais do vão)
                    self.harmony_streak += 1
                    self.max_streak_run = max(self.max_streak_run, self.harmony_streak)
                else:
                    self.harmony_streak = 0  # Passagem raspando na borda reinicia o combo

                gate.trigger_scored(clean_center)
                self.score += 1
                self.score_pop_scale = 1.34  # Pulsa o número do placar
                self.camera_shake.add_trauma(0.11 if clean_center else 0.06)
                self._emit_gate_particles(clean_center)
                self.sound.play_pentatonic(self.harmony_streak)  # Toca nota musical correspondente

        self.gates = [g for g in self.gates if not g.is_offscreen()]  # Remove portais fora da tela

    def _update_lanterns(self, dt: float, speed: float) -> None:
        """Atualiza lanternas coletáveis e detecta coleta pelo jogador."""
        for lantern in self.lanterns:
            lantern.update(dt, speed)
            dist = math.hypot(self.player.x - lantern.x, self.player.y - lantern.y)  # Distância circular
            if not lantern.collected and dist <= self.player.radius + lantern.radius + 8.0:
                lantern.collected = True
                self.score += 2  # Lanterna concede +2 pontos extras
                self.harmony_streak += 1  # Também fortalece a sequência de Harmonia
                self.max_streak_run = max(self.max_streak_run, self.harmony_streak)
                self.score_pop_scale = 1.42
                self.camera_shake.add_trauma(0.16)
                self.flash_color = Palette.GOLD_FOIL
                self.flash_alpha = 42.0
                self._emit_lantern_particles(lantern.x, lantern.y)
                self.sound.play("lantern")

        self.lanterns = [orb for orb in self.lanterns if not orb.is_offscreen()]

    def _update_vfx(self, dt: float) -> None:
        """Atualiza partículas, ondas e textos flutuantes."""
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

        for s in self.shockwaves:
            s.update(dt)
        self.shockwaves = [s for s in self.shockwaves if s.alive]

        for t in self.floating_texts:
            t.update(dt)
        self.floating_texts = [t for t in self.floating_texts if t.alive]

    def _check_collisions(self) -> None:
        """Verifica colisões com solo e portais."""
        if self.player.y + self.player.radius >= PLAYABLE_HEIGHT:  # Tocou o chão
            self.player.y = PLAYABLE_HEIGHT - self.player.radius
            self._trigger_game_over()
            return

        hitbox = self.player.get_hitbox()  # Caixa de colisão justa do tsuru
        for gate in self.gates:
            if hitbox.colliderect(gate.top_rect) or hitbox.colliderect(gate.bottom_rect):
                self._trigger_game_over()
                return

    # -------------------------------------------------------------------------
    # RENDERIZAÇÃO DE CENA E INTERFACE
    # -------------------------------------------------------------------------

    def _draw(self) -> None:
        """Renderiza cena em camadas ordenadas + sobreposições de estado."""
        cam_offset = self.camera_shake.get_offset()  # Tremor do quadro atual
        self.fx_layer.fill((0, 0, 0, 0))  # Limpa camada transparente antes de desenhar o frame

        self.world.draw_backdrop(self.screen, self.fx_layer, cam_offset)

        for gate in self.gates:
            gate.draw(self.screen, self.fx_layer, cam_offset)

        for lantern in self.lanterns:
            lantern.draw(self.screen, self.fx_layer, cam_offset)

        for shockwave in self.shockwaves:
            shockwave.draw(self.fx_layer, cam_offset)

        for particle in self.particles:
            particle.draw(self.fx_layer, cam_offset)

        self.player.draw(self.screen, self.fx_layer, cam_offset)
        self.screen.blit(self.fx_layer, (0, 0))  # Descarrega todos os efeitos alfa de uma só vez

        self.world.draw_ground(self.screen, cam_offset)  # Solo por cima da base dos pilares

        for ftext in self.floating_texts:
            ftext.draw(self.screen, cam_offset)

        if self.flash_alpha > 1.0:  # Flash translúcido sobre toda a tela em impactos ou lanternas
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((*self.flash_color, int(self.flash_alpha)))
            self.screen.blit(flash, (0, 0))

        # Desenha a camada de interface correspondente ao estado atual
        if self.state == GameState.MENU:
            self._draw_menu_ui()
        elif self.state == GameState.JOGANDO:
            self._draw_hud()
        elif self.state == GameState.PAUSADO:
            self._draw_hud()
            self._draw_pause_overlay()
        elif self.state == GameState.GAME_OVER:
            self._draw_gameover_overlay()

        self._draw_mute_button()  # Botão de áudio sempre visível no canto superior direito
        pygame.display.flip()  # Atualiza o buffer visível da janela

    def _draw_mute_button(self) -> None:
        """Ícone minimalista no canto superior direito para silenciar o áudio."""
        surf = pygame.Surface((self.mute_rect.width, self.mute_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(
            surf,
            (*Palette.CARD_BG, 165),
            (0, 0, self.mute_rect.width, self.mute_rect.height),
            border_radius=10,
        )
        border = Palette.WING_ACCENT if self.sound.muted else Palette.GOLD_FOIL
        pygame.draw.rect(
            surf,
            (*border, 185),
            (0, 0, self.mute_rect.width, self.mute_rect.height),
            width=1,
            border_radius=10,
        )
        self.screen.blit(surf, self.mute_rect.topleft)

        cx, cy = self.mute_rect.center
        col = Palette.TEXT_MUTED if self.sound.muted else Palette.TEXT_CREAM
        speaker = [  # Polígono geométrico do alto-falante
            (cx - 8, cy - 4),
            (cx - 3, cy - 4),
            (cx + 3, cy - 8),
            (cx + 3, cy + 8),
            (cx - 3, cy + 4),
            (cx - 8, cy + 4),
        ]
        pygame.draw.polygon(self.screen, col, speaker)
        if self.sound.muted:  # Desenha um "X" coral quando está silenciado
            pygame.draw.line(
                self.screen, Palette.WING_ACCENT, (cx + 6, cy - 5), (cx + 12, cy + 5), 2
            )
            pygame.draw.line(
                self.screen, Palette.WING_ACCENT, (cx + 12, cy - 5), (cx + 6, cy + 5), 2
            )
        else:  # Desenha arco de onda sonora quando ativo
            pygame.draw.arc(self.screen, Palette.GOLD_FOIL, (cx + 3, cy - 6, 8, 12), -1.0, 1.0, 2)

    def _draw_hud(self) -> None:
        """Exibe pontuação, selo discreto de recorde e indicador de harmonia."""
        score_str = str(self.score)
        shadow = self.font_score.render(score_str, True, Palette.INK_SHADOW)
        main = self.font_score.render(score_str, True, Palette.TEXT_CREAM)

        if abs(self.score_pop_scale - 1.0) > 0.01:  # Redimensiona placar durante o efeito pop
            w = int(main.get_width() * self.score_pop_scale)
            h = int(main.get_height() * self.score_pop_scale)
            main = pygame.transform.smoothscale(main, (w, h))
            shadow = pygame.transform.smoothscale(shadow, (w, h))

        center = (SCREEN_WIDTH // 2, 56)
        glow = get_glow_surface(36, Palette.GOLD_FOIL, max_alpha=58)
        glow_pos = (center[0] - glow.get_width() // 2, center[1] - glow.get_height() // 2)
        self.screen.blit(glow, glow_pos)
        self.screen.blit(shadow, shadow.get_rect(center=(center[0] + 2, center[1] + 4)))
        self.screen.blit(main, main.get_rect(center=center))

        if self.harmony_streak >= 2:  # Só exibe o multiplicador a partir de 2 acertos seguidos
            draw_text_with_shadow(
                self.screen,
                self.font_small,
                f"HARMONIA x{self.harmony_streak}",
                Palette.JADE_MIST,
                (SCREEN_WIDTH // 2, 94),
                shadow_offset=(1, 2),
            )

        # Pílula translúcida com o recorde atual no canto superior esquerdo
        pill = pygame.Surface((136, 32), pygame.SRCALPHA)
        pygame.draw.rect(pill, (*Palette.CARD_BG, 165), (0, 0, 136, 32), border_radius=16)
        pygame.draw.rect(
            pill, (*Palette.GOLD_FOIL, 130), (0, 0, 136, 32), width=1, border_radius=16
        )
        self.screen.blit(pill, (16, 18))

        best = max(self.score, self.highscore_manager.high_score)
        draw_text_with_shadow(
            self.screen,
            self.font_small,
            f"RECORDE: {best}",
            Palette.GOLD_FOIL,
            (84, 34),
            shadow_offset=(1, 1),
        )

    def _draw_menu_ui(self) -> None:
        """Renderiza título artesanal sobre a demonstração viva ao crepúsculo."""
        veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        veil.fill((*Palette.SKY_ZENITH, 65))  # Véu leve para aumentar leitura sem esconder o fundo
        self.screen.blit(veil, (0, 0))

        bob = math.sin(self.ui_time * 2.2) * 7.0  # Flutuação suave vertical do título
        title_y = int(172 + bob)

        glow = get_glow_surface(110, Palette.GOLD_FOIL, max_alpha=72)
        self.screen.blit(
            glow,
            (SCREEN_WIDTH // 2 - glow.get_width() // 2, title_y - glow.get_height() // 2),
        )

        draw_text_with_shadow(
            self.screen,
            self.font_title,
            "TSURU",
            Palette.TEXT_CREAM,
            (SCREEN_WIDTH // 2, title_y),
            shadow_offset=(3, 5),
        )
        draw_text_with_shadow(
            self.screen,
            self.font_small,
            "VENTOS DO CREPÚSCULO",
            Palette.GOLD_FOIL,
            (SCREEN_WIDTH // 2, title_y + 42),
            shadow_offset=(1, 2),
        )

        # Emblema de recorde salvo em disco
        badge = pygame.Surface((224, 42), pygame.SRCALPHA)
        pygame.draw.rect(badge, (*Palette.CARD_BG, 185), (0, 0, 224, 42), border_radius=21)
        pygame.draw.rect(
            badge, (*Palette.GOLD_FOIL, 145), (0, 0, 224, 42), width=1, border_radius=21
        )
        self.screen.blit(badge, (SCREEN_WIDTH // 2 - 112, 256))
        draw_text_with_shadow(
            self.screen,
            self.font_body,
            f"RECORDE: {self.highscore_manager.high_score}",
            Palette.GOLD_FOIL,
            (SCREEN_WIDTH // 2, 277),
            shadow_offset=(1, 2),
        )

        # Texto de início com pulso contínuo de opacidade
        pulse_alpha = int(155 + 100 * (0.5 + 0.5 * math.sin(self.ui_time * 3.8)))
        draw_text_with_shadow(
            self.screen,
            self.font_button,
            "Pressione ESPAÇO para iniciar",
            Palette.TEXT_CREAM,
            (SCREEN_WIDTH // 2, 502),
            shadow_offset=(2, 3),
            alpha=pulse_alpha,
        )
        draw_text_with_shadow(
            self.screen,
            self.font_small,
            "ESPAÇO / CLIQUE: Voar   •   P: Pausar   •   M: Som",
            Palette.TEXT_MUTED,
            (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 34),
            shadow_offset=(1, 1),
        )

    def _draw_pause_overlay(self) -> None:
        """Painel de pausa com moldura dupla e fundo fosco suave."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*Palette.INK_SHADOW, 165))  # Escurece a cena congelada por trás
        self.screen.blit(overlay, (0, 0))

        panel_rect = pygame.Rect(SCREEN_WIDTH // 2 - 155, 222, 310, 320)
        self._draw_framed_panel(panel_rect, Palette.GOLD_FOIL, alpha=238)

        draw_text_with_shadow(
            self.screen,
            self.font_heading,
            "PAUSA",
            Palette.TEXT_CREAM,
            (SCREEN_WIDTH // 2, 268),
        )
        draw_text_with_shadow(
            self.screen,
            self.font_body,
            f"Pontuação Atual: {self.score}",
            Palette.TEXT_MUTED,
            (SCREEN_WIDTH // 2, 308),
        )

        self.btn_resume.draw(self.screen)
        self.btn_pause_restart.draw(self.screen)
        self.btn_pause_menu.draw(self.screen)

    def _draw_gameover_overlay(self) -> None:
        """Transição suave de Fim de Voo com pontuação, recorde e classificação."""
        t = ease_out_cubic(min(1.0, self.game_over_timer / 0.42))  # Entrada animada de 0.42s
        overlay_alpha = int(175 * t)
        card_alpha = int(245 * t)
        slide_offset = int((1.0 - t) * 46)  # Desliza 46 px de baixo para cima ao aparecer

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*Palette.INK_SHADOW, overlay_alpha))
        self.screen.blit(overlay, (0, 0))

        panel_rect = pygame.Rect(SCREEN_WIDTH // 2 - 168, 162 + slide_offset, 336, 286)
        border = Palette.GOLD_FOIL if self.is_new_record else Palette.WING_ACCENT
        self._draw_framed_panel(panel_rect, border, alpha=card_alpha)

        draw_text_with_shadow(
            self.screen,
            self.font_heading,
            "FIM DE VOO",
            Palette.WING_ACCENT,
            (SCREEN_WIDTH // 2, 206 + slide_offset),
            alpha=card_alpha,
        )

        if self.is_new_record:  # Destaque especial caso tenha superado o recorde anterior
            draw_text_with_shadow(
                self.screen,
                self.font_small,
                "— NOVO RECORDE ALCANÇADO —",
                Palette.GOLD_FOIL,
                (SCREEN_WIDTH // 2, 240 + slide_offset),
                alpha=card_alpha,
            )

        draw_text_with_shadow(
            self.screen,
            self.font_small,
            "PONTUAÇÃO",
            Palette.TEXT_MUTED,
            (SCREEN_WIDTH // 2 - 76, 278 + slide_offset),
            alpha=card_alpha,
        )
        draw_text_with_shadow(
            self.screen,
            self.font_score,
            str(self.score),
            Palette.TEXT_CREAM,
            (SCREEN_WIDTH // 2 - 76, 322 + slide_offset),
            alpha=card_alpha,
        )

        draw_text_with_shadow(
            self.screen,
            self.font_small,
            "RECORDE",
            Palette.TEXT_MUTED,
            (SCREEN_WIDTH // 2 + 76, 278 + slide_offset),
            alpha=card_alpha,
        )
        draw_text_with_shadow(
            self.screen,
            self.font_score,
            str(self.highscore_manager.high_score),
            Palette.GOLD_FOIL,
            (SCREEN_WIDTH // 2 + 76, 322 + slide_offset),
            alpha=card_alpha,
        )

        draw_text_with_shadow(
            self.screen,
            self.font_small,
            f"MELHOR HARMONIA: x{max(self.max_streak_run, self.highscore_manager.best_streak)}",
            Palette.JADE_MIST,
            (SCREEN_WIDTH // 2, 376 + slide_offset),
            alpha=card_alpha,
        )

        rank_title, rank_color = self._get_poetic_rank(self.score)
        draw_text_with_shadow(
            self.screen,
            self.font_body,
            rank_title,
            rank_color,
            (SCREEN_WIDTH // 2, 412 + slide_offset),
            alpha=card_alpha,
        )

        self.btn_restart.draw(self.screen, y_offset=slide_offset, alpha=card_alpha)
        self.btn_gameover_menu.draw(self.screen, y_offset=slide_offset, alpha=card_alpha)

        draw_text_with_shadow(
            self.screen,
            self.font_small,
            "Atalho: ESPAÇO ou R para reiniciar",
            Palette.TEXT_MUTED,
            (SCREEN_WIDTH // 2, 610 + slide_offset),
            alpha=card_alpha,
        )

    @staticmethod
    def _get_poetic_rank(score: int) -> Tuple[str, Tuple[int, int, int]]:
        """Define um título poético para o voo conforme a pontuação."""
        if score >= 45:
            return ("Espírito do Crepúsculo", Palette.GOLD_FOIL)
        if score >= 28:
            return ("Guardião dos Ventos", Palette.JADE_MIST)
        if score >= 14:
            return ("Asa de Seda", Palette.TEXT_CREAM)
        if score >= 6:
            return ("Brisa Dourada", Palette.PETAL_ROSE)
        return ("Primeiro Voo", Palette.TEXT_MUTED)

    def _draw_framed_panel(
        self,
        rect: pygame.Rect,
        border_color: Tuple[int, int, int],
        alpha: int = 235,
    ) -> None:
        """Renderiza painel com sombra projetada e moldura dupla artesanal."""
        shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(
            shadow,
            (*Palette.INK_SHADOW, int(150 * (alpha / 255.0))),
            (0, 0, rect.width, rect.height),
            border_radius=14,
        )
        self.screen.blit(shadow, (rect.x + 6, rect.y + 9))  # Sombra deslocada para baixo/direita

        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(
            panel,
            (*Palette.CARD_BG, alpha),
            (0, 0, rect.width, rect.height),
            border_radius=14,
        )
        pygame.draw.rect(
            panel,
            (*border_color, alpha),
            (0, 0, rect.width, rect.height),
            width=2,  # Borda externa principal
            border_radius=14,
        )
        pygame.draw.rect(
            panel,
            (*border_color, int(alpha * 0.42)),
            (6, 6, rect.width - 12, rect.height - 12),
            width=1,  # Moldura interna fina
            border_radius=10,
        )
        self.screen.blit(panel, rect.topleft)

    def run(self) -> None:
        """Loop principal travado a 60 FPS com física via Delta Time."""
        while self.running:
            raw_dt = self.clock.tick(FPS) / 1000.0  # Espera até 60 FPS e mede segundos do quadro
            dt = min(raw_dt, MAX_DT)  # Aplica teto de segurança para física estável

            self._handle_events()  # 1. Lê teclado e mouse
            self._update(dt)       # 2. Atualiza simulação física e efeitos
            self._draw()           # 3. Desenha todo o quadro na tela

        pygame.quit()  # Libera recursos gráficos e sonoros ao encerrar


if __name__ == "__main__":  # Garante que o jogo só inicia se o arquivo for executado diretamente
    Game().run()


# =============================================================================
# GUIA RÁPIDO DE INSTALAÇÃO E EXECUÇÃO
# =============================================================================
# 1. Instale o Pygame:
#    pip install pygame
#    (No PowerShell do Windows, caso `pip` não esteja no PATH: py -m pip install pygame)
#
# 2. Execute o jogo no terminal:
#    python tsuru_origami.py
#    (No Windows, com o launcher padrão: py tsuru_origami.py)
#
# Controles:
# - ESPAÇO / Seta Cima / Clique Esquerdo: Bater asas / Iniciar
# - P / ESC: Pausar ou retomar
# - R: Reinício instantâneo no Fim de Voo ou Pausa
# - M: Silenciar / ativar áudio procedural
# =============================================================================
