import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { Team, JoinRequest, PaginatedResponse } from '../models';

@Injectable({ providedIn: 'root' })
export class TeamService {
  private readonly apiUrl = `${environment.apiUrl}/teams`;

  constructor(private http: HttpClient) {}

  getTeams(): Observable<PaginatedResponse<Team>> {
    return this.http.get<PaginatedResponse<Team>>(this.apiUrl + '/');
  }

  getTeam(id: number): Observable<Team> {
    return this.http.get<Team>(`${this.apiUrl}/${id}/`);
  }

  getMyTeam(): Observable<Team> {
    return this.http.get<Team>(`${this.apiUrl}/my/`);
  }

  createTeam(data: { name: string; description?: string }): Observable<Team> {
    return this.http.post<Team>(`${this.apiUrl}/create/`, data);
  }

  requestJoin(teamId: number): Observable<JoinRequest> {
    return this.http.post<JoinRequest>(`${this.apiUrl}/${teamId}/join/`, {});
  }

  getRequests(teamId: number): Observable<JoinRequest[]> {
    return this.http.get<JoinRequest[]>(`${this.apiUrl}/${teamId}/requests/`);
  }

  handleRequest(requestId: number, action: 'accept' | 'reject'): Observable<any> {
    return this.http.post(`${this.apiUrl}/requests/${requestId}/handle/`, { action });
  }

  leaveTeam(): Observable<any> {
    return this.http.post(`${this.apiUrl}/leave/`, {});
  }

  promoteMember(memberId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/members/${memberId}/promote/`, {});
  }

  kickMember(memberId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/members/${memberId}/kick/`, {});
  }

  uploadLogo(file: File): Observable<{ logo_url: string }> {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('upload_preset', environment.cloudinaryUploadPreset);
    fd.append('folder', 'deckshado/team_logos');
    return this.http.post<any>(
      `https://api.cloudinary.com/v1_1/${environment.cloudinaryCloudName}/image/upload`, fd
    ).pipe(
      switchMap(res => this.http.post<{ logo_url: string }>(`${this.apiUrl}/logo/`, { logo_url: res.secure_url }))
    );
  }
}
