import { Component, Input, OnInit, ElementRef, ViewChild } from '@angular/core';

@Component({
  selector: 'app-toon-viewer',
  template: `
    <div class="toon-viewer-container">
      <h3>Visualização TOON 3D (Simulação)</h3>
      <p>Handover: {{ handoverId }}</p>
      <div class="viewer-placeholder">
        <!-- Placeholder for a 3D canvas rendering the TOON -->
        <canvas #toonCanvas width="400" height="300"></canvas>
      </div>
      <div class="controls">
        <button (click)="rotate()">Rotacionar</button>
        <button (click)="zoom()">Zoom</button>
      </div>
    </div>
  `,
  styles: [
    `.toon-viewer-container { border: 1px solid #ccc; padding: 10px; border-radius: 8px; }`,
    `.viewer-placeholder { background-color: #f0f0f0; text-align: center; margin: 10px 0; }`,
    `canvas { border: 1px solid #999; }`,
    `.controls button { margin-right: 5px; }`
  ]
})
export class ToonViewerComponent implements OnInit {
  @Input() handoverId: string = 'unknown';
  @ViewChild('toonCanvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;

  ngOnInit() {
    this.renderPlaceholder();
  }

  renderPlaceholder() {
    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = '#e0e0e0';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#333';
      ctx.font = '16px Arial';
      ctx.fillText('TOON 3D Viewer Area', 120, 150);
      ctx.fillText(`Carregando handover ${this.handoverId}...`, 100, 180);
    }
  }

  rotate() {
    console.log('Rotacionando modelo 3D TOON...');
  }

  zoom() {
    console.log('Aplicando zoom no modelo 3D TOON...');
  }
}
