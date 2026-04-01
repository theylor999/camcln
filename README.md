# CamMic

Compartilha a webcam do notebook para outro PC pela rede WiFi.
Funciona como o DroidCam, mas de PC para PC. A câmera aparece no Discord, Teams, etc.

---

## Como funciona

```
Notebook (server.py) ──MJPEG/WiFi──► PC do Discord (client.py) ──► câmera virtual ──► Discord
```

---

## Pré-requisitos

### Em ambos os PCs
- Python 3.9+

### Só no PC do Discord (cliente)
- **OBS Studio** instalado (cria o driver de câmera virtual)
  - Baixe em: https://obsproject.com/
  - Só instala — não precisa abrir o OBS

---

## Instalação

```bash
pip install -r requirements.txt
```

> No PC cliente, instale o OBS **antes** de rodar esse comando.

---

## Uso

### 1. No notebook (com a webcam)

```bash
python server.py
```

- Selecione a câmera desejada
- Clique em **Iniciar Stream**
- Anote o endereço exibido (ex: `192.168.1.10:5000`)

### 2. No PC do Discord

```bash
python client.py
```

- Cole o IP do notebook no campo
- Clique em **Conectar**
- Quando aparecer `Câmera virtual ativa: "OBS Virtual Camera"`, vá ao Discord

### 3. No Discord

`Configurações → Voz e Vídeo → Câmera → selecionar "OBS Virtual Camera"`

---

## Solução de problemas

| Problema | Solução |
|----------|---------|
| Cliente não conecta | Verifique se ambos estão na mesma rede WiFi. Verifique o IP no server.py |
| "pyvirtualcam não instalado" | Instale o OBS Studio primeiro, depois `pip install pyvirtualcam` |
| Câmera não aparece no Discord | Reinicie o Discord após conectar o CamMic |
| Firewall bloqueia | Libere a porta 5000 no Firewall do Windows no notebook |
| Tela preta no preview | Troque a câmera no dropdown do server.py |
